import json
import os
import time
import unittest
from unittest.mock import Mock, patch

import requests

from instances.steam_auto import SteamAuto
from steam.SteamAPI import SteamAPI


class SteamNewsFetchTests(unittest.TestCase):
    def test_requests_full_news_content(self):
        api = SteamAPI("steam-key")
        response = Mock()
        response.json.return_value = {"appnews": {"newsitems": []}}
        api.session.get = Mock(return_value=response)

        api.get_steam_news(app_id=730, count=10)

        params = api.session.get.call_args.kwargs["params"]
        self.assertEqual(params["maxlength"], 0)


class SteamNewsTranslationTests(unittest.TestCase):
    def setUp(self):
        self.instance = SteamAuto.__new__(SteamAuto)

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "deepseek-key"}, clear=False)
    @patch("instances.steam_auto.requests.post")
    def test_retries_translation_once_then_returns_chinese(self, post):
        success = Mock()
        success.json.return_value = {
            "choices": [{
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps({
                        "title": "更新说明",
                        "contents": "这是完整的中文正文。",
                    }, ensure_ascii=False)
                }
            }]
        }
        post.side_effect = [requests.Timeout("timeout"), success]

        result = self.instance._translate_cs2_news("Update Notes", "Full English body.")

        self.assertEqual(result, ("更新说明", "这是完整的中文正文。", True))
        self.assertEqual(post.call_count, 2)

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "deepseek-key"}, clear=False)
    @patch("instances.steam_auto.requests.post")
    def test_falls_back_to_complete_english_after_two_failures(self, post):
        post.side_effect = requests.Timeout("timeout")

        result = self.instance._translate_cs2_news("Update Notes", "Full English body.")

        self.assertEqual(result, ("Update Notes", "Full English body.", False))
        self.assertEqual(post.call_count, 2)

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "deepseek-key"}, clear=False)
    @patch("instances.steam_auto.requests.post")
    def test_retries_malformed_json_shape_then_falls_back_to_english(self, post):
        malformed = Mock()
        malformed.json.return_value = {
            "choices": [{"finish_reason": "stop", "message": {"content": "[]"}}]
        }
        post.return_value = malformed

        result = self.instance._translate_cs2_news("Update Notes", "Full English body.")

        self.assertEqual(result, ("Update Notes", "Full English body.", False))
        self.assertEqual(post.call_count, 2)

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "deepseek-key"}, clear=False)
    @patch("instances.steam_auto.requests.post")
    def test_incomplete_deepseek_response_is_retried_then_falls_back(self, post):
        incomplete = Mock()
        incomplete.json.return_value = {
            "choices": [{
                "finish_reason": "length",
                "message": {"content": json.dumps({"title": "标题", "contents": "半段"})},
            }]
        }
        post.return_value = incomplete

        result = self.instance._translate_cs2_news("Update Notes", "Full English body.")

        self.assertEqual(result, ("Update Notes", "Full English body.", False))
        self.assertEqual(post.call_count, 2)

    @patch.dict(os.environ, {"DEEPSEEK_API_KEY": "deepseek-key"}, clear=False)
    @patch("instances.steam_auto.requests.post")
    def test_translates_long_body_in_segments_and_reassembles_all_output(self, post):
        first = Mock()
        first.json.return_value = {
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": json.dumps({"title": "中文标题", "contents": "第一段\n"}, ensure_ascii=False)},
            }]
        }
        second = Mock()
        second.json.return_value = {
            "choices": [{
                "finish_reason": "stop",
                "message": {"content": json.dumps({"title": "中文标题", "contents": "第二段"}, ensure_ascii=False)},
            }]
        }
        post.side_effect = [first, second]
        body = ("A" * 4000) + "\n" + ("B" * 4000)

        result = self.instance._translate_cs2_news("Update Notes", body)

        self.assertEqual(result, ("中文标题", "第一段\n第二段", True))
        self.assertEqual(post.call_count, 2)

    def test_cleans_html_and_common_steam_bbcode_without_truncating(self):
        source = (
            '<p>Fixes &amp; changes</p><br>[b]Important[/b]: '
            '[url=https://example.com]details[/url]'
            '<ul><li><a href="https://html.example">HTML link</a></li></ul>'
            '[img]https://example.com/image.png[/img]'
        )

        result = self.instance._clean_cs2_news_contents(source)

        self.assertEqual(
            result,
            "Fixes & changes\n\nImportant: details (https://example.com)\n"
            "• HTML link (https://html.example)\n\n图片：https://example.com/image.png",
        )

    def test_splits_long_messages_without_losing_content(self):
        source = ("A" * 1200) + "\n" + ("B" * 1200) + "\n" + ("C" * 1200)

        chunks = self.instance._split_cs2_news_message(source, max_length=1800)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk) <= 1800 for chunk in chunks))
        self.assertEqual("".join(chunks), source)

    def test_preserves_compact_steam_headings_and_list_items(self):
        source = (
            '[h2][ UI ][/h2][p]演示/回放查看器改进：[/p]'
            '[list][*]下载进度条[/*][*]点击并拖拽[/*][/list]'
            '<h2>[ 杂项 ]</h2><ul><li>回合备份启动标志</li>'
            '<li>AUG 换弹动画</li></ul>'
        )

        self.assertEqual(
            self.instance._clean_cs2_news_contents(source),
            '【UI】\n演示/回放查看器改进：\n• 下载进度条\n• 点击并拖拽'
            '\n\n【杂项】\n• 回合备份启动标志\n• AUG 换弹动画',
        )

    def test_joins_bullets_split_by_html_paragraphs(self):
        source = (
            '<h2>[ 游戏玩法 ]</h2><ul><li><p>新增静音换弹选项。</p></li>'
            '<li><p>修复换弹声音。</p></li></ul>'
            '[h2][ 杂项 ][/h2][list][*][p]修复 AMD 显卡渲染。[/*][/p][/list]'
        )

        self.assertEqual(
            self.instance._clean_cs2_news_contents(source),
            '【游戏玩法】\n• 新增静音换弹选项。\n• 修复换弹声音。'
            '\n\n【杂项】\n• 修复 AMD 显卡渲染。',
        )

    def test_normalizes_translated_plain_text_for_wechat(self):
        source = (
            '\\[ 游戏玩法 ]\r\n\r\n-\r\n\r\n新增静音换弹选项。'
            '\r\n\r\n-\r\n\r\n修复换弹声音。'
            '\r\n\r\n\\[ 杂项 \\]\r\n\r\n- 修复 AMD 显卡渲染。'
        )
        expected = (
            '【游戏玩法】\n• 新增静音换弹选项。\n• 修复换弹声音。'
            '\n\n【杂项】\n• 修复 AMD 显卡渲染。'
        )

        self.assertEqual(self.instance._clean_cs2_news_contents(source), expected)
        self.assertEqual(self.instance._clean_cs2_news_contents(expected), expected)


class SteamNewsDeliveryTests(unittest.TestCase):
    def test_sends_translated_full_news_and_only_then_caches_gid(self):
        instance = SteamAuto.__new__(SteamAuto)
        instance.enable_news_check = True
        instance.cached_news_gids = {"old": time.time()}
        instance.steam = Mock()
        instance.steam.get_steam_news.return_value = [{
            "gid": "new",
            "title": "English title",
            "contents": "<p>Full English body.</p>",
            "url": "https://example.com/update",
        }]
        instance._clean_news_cache = Mock()
        instance._trim_news_cache = Mock()
        instance.save_news_cache = Mock()
        instance._translate_cs2_news = Mock(return_value=(
            "中文标题", "\\[ UI ]\n\n-\n\n完整中文正文。", True,
        ))
        sent = []
        instance.send_message = sent.append

        instance.check_cs2_news()

        instance._translate_cs2_news.assert_called_once_with("English title", "Full English body.")
        self.assertIn("中文标题", "".join(sent))
        self.assertIn("完整中文正文。", "".join(sent))
        self.assertIn("【UI】\n• 完整中文正文。", "".join(sent))
        self.assertNotIn("[*]", "".join(sent))
        self.assertNotIn("Full English body.", "".join(sent))
        self.assertIn("new", instance.cached_news_gids)
        instance.save_news_cache.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
