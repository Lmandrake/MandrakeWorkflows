import subprocess, unittest, pathlib
H = str(pathlib.Path(__file__).resolve().parents[1] / "bin" / "term-bg-launch")

class T(unittest.TestCase):
    def test_dry_run_minimizes_and_quotes(self):
        o = subprocess.run([H, "--dry-run", 'launch "X"'], capture_output=True, text=True).stdout
        self.assertIn('do script "launch \\"X\\""', o); self.assertIn("miniaturize=true", o)
    def test_opt_out(self):
        o = subprocess.run([H, "--dry-run", "x"], capture_output=True, text=True, env={"WAYPOINT_NO_MINIMIZE": "1", "PATH": "/usr/bin:/bin"}).stdout
        self.assertIn("miniaturize=false", o)
if __name__ == "__main__": unittest.main()
