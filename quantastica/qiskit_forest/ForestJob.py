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
import sys
import functools
import os
import time
import subprocess
import json
import tempfile
import requests

from quantastica import qconvert
from qiskit.providers import BaseJob, JobStatus, JobError
from qiskit.qobj import validate_qobj_against_schema
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

class ForestJob(BaseJob):

    _executor = futures.ThreadPoolExecutor()

    def __init__(self, backend, job_id, qobj, lattice_name = None, as_qvm = False):
        super().__init__(backend, job_id)
        self._lattice_name = lattice_name
        self._as_qvm = as_qvm
        self._result = None
        self._qobj = qobj
        self._future = None

    def submit(self):
        if self._future is not None:
            raise JobError("We have already submitted the job!")

        validate_qobj_against_schema(self._qobj)
        self._future = self._executor.submit(self._run_with_rigetti)

    def wait(self, timeout=None):
        if self.status() is JobStatus.RUNNING :
            futures.wait([self._future], timeout);
        if self._future.exception() :
            raise self._future.exception()

    def result(self, timeout=None):
        self.wait(timeout)
        return Result.from_dict(self._result);

    def cancel(self):
        return

    def status(self):
        # The order is important here
        if self._future is None:
            _status = JobStatus.INITIALIZING
        elif self._future.running():
            _status = JobStatus.RUNNING
        elif self._future.cancelled():
            _status = JobStatus.CANCELLED
        elif self._future.done():
            _status = JobStatus.DONE if self._future.exception() is None else JobStatus.ERROR
        else:
            # Note: There is an undocumented Future state: PENDING, that seems to show up when
            # the job is enqueued, waiting for someone to pick it up. We need to deal with this
            # state but there's no public API for it, so we are assuming that if the job is not
            # in any of the previous states, is PENDING, ergo INITIALIZING for
            # us.
            _status = JobStatus.INITIALIZING

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

    @staticmethod     
    def _execute_rigetti(qobj, shots, lattice_name, as_qvm):

        conversion_options = { "all_experiments": False, 
            "create_exec_code": False, 
            "lattice": lattice_name, 
            "as_qvm": as_qvm,
            "shots": shots }

        pyquilstr = qconvert.convert(
            qconvert.Format.QOBJ,
            qobj.to_dict(),
            qconvert.Format.PYQUIL,
            conversion_options)
        global_vars=dict()
        counts = {}
        code = compile(pyquilstr, 'converted_qobj.py', 'exec')
        exec(code, global_vars)
        qc=global_vars['qc']

        if lattice_name is not None and lattice_name == "statevector_simulator":
            p=global_vars['p']

            wf = qc.wavefunction(p)
            state = np.array((np.real(wf.amplitudes), np.imag(wf.amplitudes))).T

            # Do we need counds in "statevector_simulator" results?
            # if so, implement weighted random over returned amplitudes instead running program twice
            #counts=qc.run_and_measure(p)
            #counts = ForestJob._convert_counts(counts)

            return { "state": state, "counts": counts }
        else:
            ex=global_vars['ex']

            counts=qc.run(ex)
            counts = ForestJob._convert_counts(counts)
            return { "counts": counts }

    def _run_with_rigetti(self):            
        qobj_dict = self._qobj.to_dict()
        shots = qobj_dict['config']['shots']
        res = ForestJob._execute_rigetti(
            self._qobj, 
            shots,
            self._lattice_name,
            self._as_qvm)

        rawversion = "0.0.1"
        qobjid = qobj_dict['qobj_id']
        qobj_header = qobj_dict['header']
        exp_dict = qobj_dict['experiments'][0]
        exp_header = exp_dict['header']
        expname = exp_header['name']
        data = dict()

        data['counts'] = {}
        if self._lattice_name == "statevector_simulator":
            data['counts'] = res['counts']
            data['statevector'] = res['state']
        else:
            data['counts'] = res['counts']

        self._result = {
            'success': True, 
            'backend_name': qobj_header['backend_name'], 
            'qobj_id': qobjid ,
            'backend_version': rawversion, 
            'header': qobj_header,
            'job_id': self._job_id, 
            'results': [
                {
                    'success': True, 
                    'meas_level': 2, 
                    'shots': shots, 
                    'data': data, 
                    'header': exp_header, 
                    'status': 'DONE', 
                    'name': expname, 
                    'seed_simulator': 0
                }
                ], 
            'status': 'COMPLETED'
        }
