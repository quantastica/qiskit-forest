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

import uuid

from quantastica.qiskit_forest import ForestJob
from qiskit.providers import BaseBackend
from qiskit.providers.models import BackendConfiguration

class ForestBackend(BaseBackend):
    MAX_QUBITS_MEMORY = 32

    DEFAULT_CONFIGURATION = {'backend_name': 'Forest',
                             'backend_version': '0.0.1',
                             'n_qubits': MAX_QUBITS_MEMORY,
                             'url': 'https://quantastica.com/',
                             'simulator': True,
                             'local': True,
                             'conditional': False,
                             'open_pulse': False,
                             'memory': True,
                             'max_shots': 65536,
                             'description': 'An Forest based qasm simulator',
                             'coupling_map': None,
                             'basis_gates': ['u1',
                                             'u2',
                                             'u3',
                                             'cx',
                                             'id',
                                             'x',
                                             'y',
                                             'z',
                                             'h',
                                             's',
                                             't'],
                             'gates': []}

    def __init__(self, configuration=None,
                provider=None,
                lattice_name = None,
                as_qvm = False):
        configuration = configuration or BackendConfiguration.from_dict(
            self.DEFAULT_CONFIGURATION)
        super().__init__(configuration=configuration, provider=provider)

        self._lattice_name = lattice_name
        self._as_qvm = as_qvm

    #@profile
    def run(self, qobj):
        job_id = str(uuid.uuid4())
        job = ForestJob.ForestJob(
            self,
            job_id,
            qobj,
            lattice_name = self._lattice_name,
            as_qvm = self._as_qvm)
        job.submit()
        return job


    #@staticmethod
    def name(self):
        backend_name = "Forest"
        if self._lattice_name is not None:
            backend_name += "_" + self._lattice_name
        return backend_name


def get_backend(lattice_name = None, as_qvm = False):
        return ForestBackend(lattice_name = lattice_name, as_qvm = as_qvm)
