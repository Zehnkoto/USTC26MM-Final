import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from colmap_points3d_to_ply import read_points3d_bin, write_ascii_ply


class ColmapPoints3DToPlyTest(unittest.TestCase):
    def test_reads_colmap_points3d_bin_and_writes_ascii_ply(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bin_path = tmp_path / "points3D.bin"
            ply_path = tmp_path / "points3D.ply"

            with bin_path.open("wb") as f:
                f.write(struct.pack("<Q", 2))
                f.write(struct.pack("<QdddBBBdQii", 11, 1.0, 2.0, 3.0, 255, 16, 8, 0.25, 1, 7, 9))
                f.write(struct.pack("<QdddBBBdQiiii", 12, -1.5, 0.0, 4.5, 1, 2, 3, 1.5, 2, 7, 10, 8, 20))

            points = read_points3d_bin(bin_path)
            write_ascii_ply(ply_path, points)
            text = ply_path.read_text(encoding="ascii")

            self.assertEqual(len(points), 2)
            self.assertIn("element vertex 2", text)
            self.assertIn("1 2 3 255 16 8", text)
            self.assertIn("-1.5 0 4.5 1 2 3", text)


if __name__ == "__main__":
    unittest.main()
