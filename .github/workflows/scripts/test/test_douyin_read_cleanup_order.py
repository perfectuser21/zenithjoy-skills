import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]

class CleanupOrderContract(unittest.TestCase):
    def test_image_transfer_cannot_delay_device_unlock(self):
        text = (ROOT / "openclaw/clawd-zenithjoy-shared-social-media/skills/douyin-phone-runtime/SKILL.md").read_text()
        self.assertIn("独立子流程禁止在持锁期间回传JPG", text)
        self.assertIn("桌面XML必须先回传并解析", text)
        self.assertIn("释放成功并回读free后才回传账号及桌面JPG", text)
        self.assertIn("图片不可读取仍判failed", text)

if __name__ == "__main__":
    unittest.main()
