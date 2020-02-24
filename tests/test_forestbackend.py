import unittest
import warnings
from quantastica.qiskit_forest import ForestBackend
from qiskit import QuantumRegister, ClassicalRegister
from qiskit import QuantumCircuit, execute, Aer
from qiskit.compiler import transpile, assemble
from numpy import pi

class TestForestBackend(unittest.TestCase):
    def setUp(self):
        """
        Ignore following warning since it seems
        that there is nothing that we can do about it
        ResourceWarning: unclosed <socket.socket fd=9, family=AddressFamily.AF_INET, type=SocketKind.SOCK_STREAM, proto=6, laddr=('127.0.0.1', 50494), raddr=('127.0.0.1', 5000)>
        """
        warnings.filterwarnings(action="ignore",
                         category=ResourceWarning)
    def tearDown(self):
        """
        Restore warnings back
        """
        warnings.filterwarnings(action="always",
                         category=ResourceWarning)


    def test_bell_counts_with_seed(self):
        shots = 1024
        qc=TestForestBackend.get_bell_qc()
        stats1 = TestForestBackend.execute_and_get_stats(
            ForestBackend.ForestBackend(),
            qc,
            shots,
            seed = 1
        )
        stats2 = TestForestBackend.execute_and_get_stats(
            ForestBackend.ForestBackend(),
            qc,
            shots,
            seed = 1
        )
        stats3 = TestForestBackend.execute_and_get_stats(
            ForestBackend.ForestBackend(),
            qc,
            shots,
            seed = 2
        )
        self.assertTrue( stats1['statevector'] is None)
        self.assertEqual( len(stats1['counts']), 2)
        self.assertEqual( stats1['totalcounts'], shots)
        self.assertEqual(stats1['counts'],stats2['counts'])
        self.assertNotEqual(stats1['counts'],stats3['counts'])

    def test_bell_counts(self):
        shots = 256
        qc=TestForestBackend.get_bell_qc()
        stats = TestForestBackend.execute_and_get_stats(
            ForestBackend.ForestBackend(),
            qc,
            shots
        )
        self.assertTrue( stats['statevector'] is None)
        self.assertEqual( len(stats['counts']), 2)
        self.assertEqual( stats['totalcounts'], shots)


    def test_bell_state_vector(self):
        """
        This is test for statevector which means that
        even with shots > 1 it should execute only one shot
        """
        shots = 256
        qc = TestForestBackend.get_bell_qc()
        stats = TestForestBackend.execute_and_get_stats(
            ForestBackend.ForestBackend(lattice_name="statevector_simulator"),
            qc,
            shots
        )
        self.assertEqual( len(stats['statevector']), 4)
        self.assertEqual( len(stats['counts']), 1)
        self.assertEqual( stats['totalcounts'], 1)

    def test_teleport_state_vector(self):
        """
        This is test for statevector which means that
        even with shots > 1 it should execute only one shot
        """
        shots = 256
        qc = TestForestBackend.get_teleport_qc()

        """
        Let's first run the aer simulation to get statevector
        and counts so we can compare those results against forest's
        """
        stats_aer = TestForestBackend.execute_and_get_stats(
            Aer.get_backend('statevector_simulator'),
            qc,
            shots
        )
        """
        Now execute forest backend
        """
        stats = TestForestBackend.execute_and_get_stats(
            ForestBackend.ForestBackend(lattice_name="statevector_simulator"),
            qc,
            shots
        )

        self.assertEqual(len(stats['counts']), len(stats_aer['counts']))
        self.assertEqual(len(stats['statevector']), len(stats_aer['statevector']))
        self.assertEqual(stats['totalcounts'], stats_aer['totalcounts'])

        """
        Let's verify that tests are working as expected
        by running fail case
        """
        stats = TestForestBackend.execute_and_get_stats(
            ForestBackend.ForestBackend(),
            qc,
            shots
        )

        self.assertNotEqual(len(stats['counts']), len(stats_aer['counts']))
        self.assertTrue(stats['statevector'] is None)
        self.assertNotEqual(stats['totalcounts'], stats_aer['totalcounts'])

    def test_multiple_jobs(self):
        qc = self.get_bell_qc()
        backend = ForestBackend.ForestBackend()
        jobs = []
        for i in range(1, 50):
            jobs.append(execute(qc, backend=backend, shots=1))
        for job in jobs:
            result = job.result()
            counts = result.get_counts(qc)
            self.assertEqual(len(counts), 1)

    def test_multiple_experiments(self):
        backend = ForestBackend.ForestBackend()
        qc_list = [ self.get_bell_qc(), self.get_teleport_qc() ]
        transpiled = transpile(qc_list, backend = backend)
        qobjs = assemble(transpiled, backend=backend, shots=4096)
        job_info = backend.run(qobjs)
        bell_counts = job_info.result().get_counts("Bell")
        tel_counts = job_info.result().get_counts("Teleport")
        self.assertEqual(len(bell_counts),2)
        self.assertEqual(len(tel_counts),4)


    @staticmethod
    def execute_and_get_stats(backend, qc, shots, seed = None):
        job = execute(qc, backend=backend, shots=shots, seed_simulator = seed)
        job_result = job.result()
        counts = job_result.get_counts(qc)
        total_counts = 0
        for c in counts:
            total_counts += counts[c]

        try:
            state_vector = job_result.get_statevector(qc)
        except:
            state_vector = None
        ret = dict()
        ret['counts'] = counts
        ret['statevector'] = state_vector
        ret['totalcounts'] = total_counts
        return ret

    @staticmethod
    def get_bell_qc():
        qc = QuantumCircuit(name="Bell")

        q = QuantumRegister(2, 'q')
        c = ClassicalRegister(2, 'c')

        qc.add_register(q)
        qc.add_register(c)

        qc.h(q[0])
        qc.cx(q[0], q[1])
        qc.measure(q[0], c[0])
        qc.measure(q[1], c[1])
        return qc

    @staticmethod
    def get_teleport_qc():
        qc = QuantumCircuit(name="Teleport")

        q = QuantumRegister(3, 'q')
        c0 = ClassicalRegister(1, 'c0')
        c1 = ClassicalRegister(1, 'c1')

        qc.add_register(q)
        qc.add_register(c0)
        qc.add_register(c1)

        qc.rx(pi / 4, q[0])
        qc.h(q[1])
        qc.cx(q[1], q[2])
        qc.cx(q[0], q[1])
        qc.h(q[0])
        qc.measure(q[1], c1[0])
        qc.x(q[2]).c_if(c1, 1)
        qc.measure(q[0], c0[0])
        qc.z(q[2]).c_if(c0, 1)
        return qc

if __name__ == '__main__':
    unittest.main()
