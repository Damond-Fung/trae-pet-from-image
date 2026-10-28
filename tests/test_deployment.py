"""Isolated behavior tests: never modify a real TRAE installation."""
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace as Args
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('petctl', ROOT / 'scripts/petctl.py')
pet = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pet)


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.media = self.base / 'fake-app' / pet.MEDIA_REL
        for key in pet.CONTRACT:
            p = pet.contract_path(self.media, key)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('native ' + key, encoding='utf-8')
        self.snapshot = self.base / 'snapshot'
        pet.inspect(Args(media=str(self.media), out=str(self.snapshot)))
        self.payload = self.base / 'payload'
        (self.payload / 'custom-pet').mkdir(parents=True)
        (self.payload / 'floatingButton.html').write_text('patched html', encoding='utf-8')
        (self.payload / 'custom-pet/renderer.js').write_text('new renderer', encoding='utf-8')
        self.bundle = self.base / 'bundle'
        pet.bundle(Args(snapshot=str(self.snapshot), payload=str(self.payload), out=str(self.bundle)))
        self.root, self.m, self.target = pet.load_bundle(self.bundle)

    def test_install_restore_and_repair(self):
        self.assertEqual(pet.status_data(self.m, self.target)['state'], 'repairable')
        self.assertEqual(pet.apply_bundle(self.root, self.m, self.target)['state'], 'installed')
        self.assertEqual(pet.apply_bundle(self.root, self.m, self.target)['state'], 'installed')
        (self.target / 'floatingButton.html').write_text('native floatingButton.html', encoding='utf-8')
        (self.target / 'custom-pet/renderer.js').unlink()
        self.assertEqual(pet.apply_bundle(self.root, self.m, self.target)['state'], 'installed')
        self.assertEqual(pet.restore(self.root, self.m, self.target)['state'], 'restored')
        self.assertEqual((self.target / 'floatingButton.html').read_text(), 'native floatingButton.html')
        self.assertFalse((self.target / 'custom-pet/renderer.js').exists())

    def test_unknown_version_refused(self):
        p = pet.contract_path(self.media, '@app/out/main.js')
        p.write_text('new client version')
        self.assertEqual(pet.status_data(self.m, self.target)['state'], 'needs-adaptation')
        with self.assertRaises(ValueError):
            pet.apply_bundle(self.root, self.m, self.target)
        self.assertEqual((self.media / 'floatingButton.html').read_text(), 'native floatingButton.html')

    def test_payload_tamper_refused(self):
        (self.bundle / 'payload/custom-pet/renderer.js').write_text('changed')
        with self.assertRaises(ValueError):
            pet.load_bundle(self.bundle)

    def test_partial_write_rolls_back(self):
        real_atomic = pet.atomic
        def fault(path, data):
            if Path(path) == self.media / 'floatingButton.html' and data == b'patched html':
                raise OSError('simulated disk error')
            return real_atomic(path, data)
        with patch.object(pet, 'atomic', fault):
            with self.assertRaises(OSError):
                pet.apply_bundle(self.root, self.m, self.target)
        self.assertFalse((self.media / 'custom-pet/renderer.js').exists())
        self.assertEqual((self.media / 'floatingButton.html').read_text(), 'native floatingButton.html')

    def test_unknown_restore_refused(self):
        pet.apply_bundle(self.root, self.m, self.target)
        (self.media / 'floatingButton.html').write_text('updater new entry')
        with self.assertRaises(ValueError):
            pet.restore(self.root, self.m, self.target)
        self.assertEqual((self.media / 'floatingButton.html').read_text(), 'updater new entry')

    def test_path_escape_refused(self):
        for p in ['../outside', '/absolute', 'C:/absolute', 'custom-pet/../../escape']:
            with self.assertRaises(ValueError):
                pet.contained(self.media, p)

    def test_periodic_unknown_state_written(self):
        pet.contract_path(self.media, '@app/out/main.js').write_text('unknown')
        result = pet.run(Args(command='repair', bundle=str(self.bundle)))
        self.assertEqual(result['state'], 'needs-adaptation')
        self.assertEqual(pet.read(self.bundle / 'update-status.json')['state'], 'needs-adaptation')


if __name__ == '__main__':
    unittest.main(verbosity=2)
