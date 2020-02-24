# This code is part of quantastica.qiskit_forest
#
# (C) Copyright Quantastica 2019.
# https://quantastica.com/
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

from concurrent import futures
import logging
import time
import copy

from quantastica import qconvert
from qiskit.providers import BaseJob, JobStatus, JobError
from qiskit.result import Result

"""
In order to speed up compiling of pyquil code we need to import
pyquil packages outside of compile/exec loop
"""
from pyquil import Program, get_qc
from pyquil.gates import *
from pyquil.quilatom import Parameter, quil_sin, quil_cos, quil_sqrt, quil_exp, quil_cis
from pyquil.quilbase import DefGate
import numpy as np

logger = logging.getLogger(__name__)

def _run_with_rigetti_static(qobj_dict, shots, lattice_name, as_qvm, job_id):
    SEED_SIMULATOR_KEY = "seed_simulator"
    seed = None
    if SEED_SIMULATOR_KEY in qobj_dict['config']:
        seed =  qobj_dict['config'][SEED_SIMULATOR_KEY]

    conversion_options = { "all_experiments": False,
        "create_exec_code": False,
        "lattice": lattice_name,
        "as_qvm": as_qvm,
        "shots": shots,
        "seed": seed }
    pyquilstr = qconvert.convert(
        qconvert.Format.QOBJ,
        qobj_dict,
        qconvert.Format.PYQUIL,
        conversion_options)
    global_vars=dict()
    counts = {}
    code = compile(pyquilstr, 'converted_qobj.py', 'exec')
    exec(code, global_vars)
    qc=global_vars['qc']
    data = dict()

    if lattice_name is not None and lattice_name == "statevector_simulator":
        p=global_vars['p']

        wf = qc.wavefunction(p)
        state = np.array((np.real(wf.amplitudes), np.imag(wf.amplitudes))).T

        # We need to switch from [re1,im1],[re2,im2]... format to
        # c1, c2... format
        complex_state = []
        for s in state:
            complex_state.append(complex(s[0],s[1]))

        # Do we need counts in "statevector_simulator" results?
        # if so, implement weighted random over returned amplitudes instead running program twice?
        counts = qc.run_and_measure(p)
        counts = ForestJob._convert_counts(counts)

        data = { "statevector": complex_state, "counts": counts }
    else:
        ex=global_vars['ex']

        counts=qc.run(ex)
        counts = ForestJob._convert_counts(counts)
        data = { "counts": counts }

    exp_dict = qobj_dict['experiments'][0]
    exp_header = exp_dict['header']
    expname = exp_header['name']
    result = {
                'success': True,
                'meas_level': 2,
                'shots': shots,
                'data': data,
                'header': exp_header,
                'status': 'DONE',
                'name': expname,
                'seed_simulator': seed
            }
    return result


class ForestJob(BaseJob):

    """
    max_workers argument is set to 1 to prevent
    `rpcq._utils.RPCError: Unhandled memory fault at #x14.`
    error which happens from time to time when there are
    multiple jobs executing in parallel
    """
    _executor = futures.ThreadPoolExecutor(max_workers=1)
    _run_time = 0

    def __init__(self, backend, job_id, qobj, lattice_name = None, as_qvm = False):
        super().__init__(backend, job_id)
        self._lattice_name = lattice_name
        self._as_qvm = as_qvm
        self._result = None
        self._qobj_dict = qobj.to_dict()
        self._futures = []


    def submit(self):
        if len(self._futures)>0:
            raise JobError("We have already submitted the job!")
        self._t_submit = time.time()

        logger.debug("submitting...")
        all_exps = self._qobj_dict
        shots = all_exps['config']['shots']
        for exp in all_exps["experiments"]:
            single_exp = copy.deepcopy(all_exps)
            single_exp["experiments"]=[exp]

            self._futures.append(self._executor.submit(_run_with_rigetti_static,
                single_exp,
                shots,
                self._lattice_name,
                self._as_qvm,
                self._job_id
                )
            )

    def wait(self, timeout=None):
        if self.status() in [JobStatus.RUNNING, JobStatus.QUEUED] :
            futures.wait(self._futures, timeout)
        if self._result is None and self.status() is JobStatus.DONE :
            results = []
            for f in self._futures:
                results.append(f.result())
            qobj_dict = self._qobj_dict
            qobjid = qobj_dict['qobj_id']
            qobj_header = qobj_dict['header']
            rawversion = "1.0.0"
            self._result = {
                'success': True,
                'backend_name': "Toaster",
                'qobj_id': qobjid ,
                'backend_version': rawversion,
                'header': qobj_header,
                'job_id': self._job_id,
                'results': results,
                'status': 'COMPLETED'
            }
            ForestJob._run_time += time.time() - self._t_submit

        if len(self._futures)>0:
            for f in self._futures:
                if f.exception() :
                    raise f.exception()

    def result(self, timeout=None):
        self.wait(timeout)
        return Result.from_dict(self._result);

    def cancel(self):
        return

    def status(self):

        if len(self._futures)==0 :
            _status = JobStatus.INITIALIZING
        else :
            running = 0
            done = 0
            canceled = 0
            error = 0
            queued = 0
            for f in self._futures:
                if f.running():
                    running += 1
                elif f.cancelled():
                    canceled += 1
                elif f.done():
                    if f.exception() is None:
                        done += 1
                    else:
                        error += 1
                else:
                    queued += 1

            if error :
                _status = JobStatus.ERROR
            elif running :
                _status = JobStatus.RUNNING
            elif canceled :
                _status = JobStatus.CANCELLED
            elif done :
                _status = JobStatus.DONE
            else: # future is in pending state
                _status = JobStatus.QUEUED
        return _status

    def backend(self):
        """Return the instance of the backend used for this job."""
        return self._backend

    @staticmethod
    def _countsarray_to_hex(counts):
        bin=""
        for c in counts:
            bin="%d%s"%(c,bin)
        return hex(int(bin,2))

    @staticmethod
    def _convert_counts(counts):
        ret = dict()
        for key in counts:
            hexkey = ForestJob._countsarray_to_hex(key)
            if hexkey in ret:
                ret[hexkey]+=1
            else:
                ret[hexkey]=1
        return ret
