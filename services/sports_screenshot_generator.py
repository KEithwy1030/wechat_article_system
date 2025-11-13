#!/usr/bin/env python3
"""
体育数据截图生成服务
自动访问专业体育数据网站并生成截图
"""

import asyncio
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import subprocess
import psutil

logger = logging.getLogger(__name__)

class SportsScreenshotGenerator:
    """体育数据截图生成器"""
    
    def __init__(self):
        self.supported_sites = {
            "flashscore": {
                "name": "FlashScore",
                "url": "https://www.flashscore.com/football/",
                "priority": "high",
                "description": "专业体育数据网站，包含详细统计数据"
            },
            "sofascore": {
                "name": "SofaScore", 
                "url": "https://www.sofascore.com/football",
                "priority": "high",
                "description": "实时体育数据和统计"
            },
            "whoscored": {
                "name": "WhoScored",
                "url": "https://www.whoscored.com/",
                "priority": "high", 
                "description": "专业足球数据分析和统计"
            },
            "espn": {
                "name": "ESPN足球",
                "url": "https://www.espn.com/soccer/scoreboard",
                "priority": "medium",
                "description": "知名体育媒体数据"
            },
            "bbc_sport": {
                "name": "BBC Sport",
                "url": "https://www.bbc.com/sport/football",
                "priority": "medium",
                "description": "权威体育新闻和数据"
            }
        }
        
        self.screenshot_dir = "cache/three_source_data"
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    async def _cleanup_chrome_processes(self):
        """清理Chrome进程，避免资源冲突"""
        try:
            print("[清理] 正在清理Chrome进程...")
            # 查找并终止Chrome进程
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'chrome' in proc.info['name'].lower():
                        cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                        if '--headless' in cmdline or '--remote-debugging-port' in cmdline:
                            print(f"[清理] 终止Chrome进程: {proc.info['pid']}")
                            proc.terminate()
                            proc.wait(timeout=5)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                    pass
            print("[清理] Chrome进程清理完成。")
        except Exception as e:
            print(f"[清理] 清理Chrome进程时发生错误: {e}")
    
    def _setup_driver(self):
        """设置Chrome驱动，增强反检测能力"""
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        from pathlib import Path
        import os

        chrome_options = Options()
        chrome_options.add_argument('--headless=new') # 使用新的headless模式
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--start-maximized') # 最大化窗口，模拟真实用户
        chrome_options.add_argument('--incognito') # 隐身模式
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--log-level=3') # 减少日志输出
        chrome_options.add_argument('--silent') # 静默模式

        driver_path = None
        try:
            project_root = Path(__file__).resolve().parents[2]
            local_driver = project_root / "drivers" / "chromedriver.exe"
            if local_driver.exists():
                driver_path = str(local_driver)
                logger.info(f"使用本地 chromedriver: {driver_path}")
        except Exception as e:
            logger.warning(f"定位本地 chromedriver 失败: {e}")

        if driver_path:
            service = Service(driver_path)
        else:
            logger.info("未找到本地 chromedriver，尝试联网下载")
            service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 执行JS隐藏webdriver属性
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
            """
        })
        return driver
    
    async def generate_specific_match_screenshot(self, match_info: Dict, target_path: str, max_retries: int = 3) -> Dict:
        """
        为特定比赛生成SoccerStats.com的专业截图
        
        Args:
            match_info: 比赛信息
            target_path: 目标截图保存路径
            max_retries: 最大重试次数
            
        Returns:
            生成结果字典
        """
        match_code = match_info.get('match_code', '')
        home_team = match_info.get('home_team', '')
        away_team = match_info.get('away_team', '')
        league = match_info.get('league', '')
        match_time = match_info.get('match_time', '')
        
        print(f"=== 开始生成特定比赛截图 ===")
        print(f"比赛: {match_code} - {home_team} vs {away_team}")
        print(f"联赛: {league}")
        print(f"时间: {match_time}")
        print(f"目标路径: {target_path}")
        
        # 首先清理可能存在的Chrome进程
        await self._cleanup_chrome_processes()
        
        for attempt in range(max_retries):
            driver = None
            try:
                print(f"[尝试 {attempt + 1}/{max_retries}] 正在生成特定比赛截图...")
                driver = self._setup_driver()
                wait = WebDriverWait(driver, 30)
                
                # 访问SoccerStats.com
                soccerstats_url = "https://www.soccerstats.com/matches.asp?matchday=6&matchdayn=1"
                print(f"[信息] 正在访问SoccerStats: {soccerstats_url}")
                driver.get(soccerstats_url)
                time.sleep(5)
                
                print(f"[信息] 页面标题: {driver.title}")
                print(f"[信息] 当前URL: {driver.current_url}")
                
                # 检查页面是否正常加载
                if not driver.title or len(driver.title) < 3:
                    print(f"[警告] 页面可能未正确加载")
                    raise WebDriverException("SoccerStats页面未正确加载")
                
                # 智能搜索和匹配比赛
                match_found = await self._search_soccerstats_match(driver, wait, match_info)
                
                if match_found:
                    print(f"[成功] 找到目标比赛，开始截图")
                else:
                    print(f"[警告] 未找到目标比赛，截图当前页面")
                
                # 等待页面内容完全加载
                time.sleep(3)
                
                # 截图 - 使用完整页面截图
                await self._take_full_page_screenshot(driver, target_path)
                
                # 验证截图文件
                if os.path.exists(target_path) and os.path.getsize(target_path) > 1000:
                    file_size = os.path.getsize(target_path)
                    print(f"[成功] 特定比赛截图生成成功: {target_path}")
                    print(f"[信息] 文件大小: {file_size} bytes")
                    
                    return {
                        "success": True,
                        "screenshot_path": target_path,
                        "match_found": match_found,
                        "file_size": file_size,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    print(f"[失败] 截图文件无效或太小")
                    raise WebDriverException("截图文件无效")
                    
            except (TimeoutException, WebDriverException) as e:
                print(f"[失败] 生成特定比赛截图失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"[重试] 等待 {5 * (attempt + 1)} 秒后重试...")
                    time.sleep(5 * (attempt + 1))
                else:
                    print(f"[失败] 达到最大重试次数，放弃生成特定比赛截图")
                    return {
                        "success": False,
                        "message": f"达到最大重试次数，生成特定比赛截图失败: {e}",
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                print(f"[严重失败] 生成特定比赛截图发生未知错误: {e}")
                return {
                    "success": False,
                    "message": f"未知错误: {e}",
                    "timestamp": datetime.now().isoformat()
                }
            finally:
                if driver:
                    driver.quit()
                await self._cleanup_chrome_processes()
        
        return {
            "success": False,
            "message": "所有重试均失败，未能生成特定比赛截图",
            "timestamp": datetime.now().isoformat()
        }
    
    async def _search_soccerstats_match(self, driver, wait, match_info: Dict) -> bool:
        """
        在SoccerStats.com中搜索特定比赛并导航到详情页
        
        Args:
            driver: WebDriver实例
            wait: WebDriverWait实例
            match_info: 比赛信息
            
        Returns:
            是否找到目标比赛并成功导航
        """
        try:
            home_team = match_info.get('home_team', '')
            away_team = match_info.get('away_team', '')
            league = match_info.get('league', '')
            match_time = match_info.get('match_time', '')
            
            print(f"[SoccerStats搜索] 开始搜索比赛: {home_team} vs {away_team}")
            print(f"[SoccerStats搜索] 联赛: {league}")
            print(f"[SoccerStats搜索] 时间: {match_time}")
            
            # 队名映射（中文到英文）
            team_mapping = await self._get_team_name_mapping()
            home_en = team_mapping.get(home_team, home_team)
            away_en = team_mapping.get(away_team, away_team)
            
            print(f"[SoccerStats搜索] 英文队名: {home_en} vs {away_en}")
            
            # 时区转换
            converted_time = await self._convert_timezone(match_time, league)
            
            # 等待页面加载完成
            time.sleep(3)
            
            # 查找比赛行（传入转换后的时间和联赛信息）
            match_row = await self._find_match_row(driver, wait, home_en, away_en, home_team, away_team, converted_time, league)
            
            if match_row:
                print(f"[SoccerStats搜索] 找到比赛行，尝试点击stats按钮")
                # 尝试点击stats按钮进入详情页
                stats_clicked = await self._click_stats_button_in_row(driver, wait, match_row)
                if stats_clicked:
                    print(f"[SoccerStats搜索] 成功进入比赛详情页")
                    time.sleep(3)  # 等待详情页加载
                    return True
                else:
                    print(f"[SoccerStats搜索] 未找到stats按钮，尝试点击analysis链接")
                    # 尝试点击analysis链接
                    analysis_clicked = await self._click_analysis_button_in_row(driver, wait, match_row)
                    if analysis_clicked:
                        print(f"[SoccerStats搜索] 成功进入analysis页面")
                        time.sleep(3)
                        return True
                    else:
                        print(f"[SoccerStats搜索] 未找到可点击的链接，使用当前页面")
                        return True
            else:
                print(f"[SoccerStats搜索] 未找到匹配的比赛行")
                return False
                
        except Exception as e:
            print(f"[SoccerStats搜索] 搜索过程异常: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    async def _take_full_page_screenshot(self, driver, target_path: str) -> bool:
        """截取完整页面截图"""
        try:
            print(f"[完整截图] 开始截取完整页面...")
            
            # 获取页面总高度
            total_height = driver.execute_script("return document.body.scrollHeight")
            viewport_height = driver.execute_script("return window.innerHeight")
            
            print(f"[完整截图] 页面总高度: {total_height}px")
            print(f"[完整截图] 视口高度: {viewport_height}px")
            
            if total_height <= viewport_height:
                # 页面内容不超过一屏，直接截图
                print(f"[完整截图] 页面内容在一屏内，直接截图")
                driver.save_screenshot(target_path)
                return True
            
            # 使用JavaScript截取完整页面
            print(f"[完整截图] 使用JavaScript截取完整页面")
            
            # 方法1: 使用Selenium的完整页面截图
            original_size = driver.get_window_size()
            
            # 设置窗口大小为完整页面大小
            driver.set_window_size(1920, total_height)
            time.sleep(2)  # 等待页面重新渲染
            
            # 截取完整页面
            driver.save_screenshot(target_path)
            
            # 恢复原始窗口大小
            driver.set_window_size(original_size['width'], original_size['height'])
            
            print(f"[完整截图] 完整页面截图完成")
            return True
            
        except Exception as e:
            print(f"[完整截图] 完整页面截图失败: {str(e)}")
            # 降级到普通截图
            try:
                print(f"[完整截图] 降级到普通截图")
                driver.save_screenshot(target_path)
                return True
            except Exception as e2:
                print(f"[完整截图] 普通截图也失败: {str(e2)}")
                return False
    
    async def _convert_timezone(self, match_time: str, league: str) -> str:
        """时区转换：北京时间 + 1小时"""
        try:
            if not match_time:
                return ""
            
            print(f"[时区转换] 原始时间: {match_time}")
            
            # 解析时间格式 "2025-10-16 23:00"
            if " " in match_time:
                date_part, time_part = match_time.split(" ")
                if ":" in time_part:
                    hour, minute = time_part.split(":")
                    hour = int(hour)
                    minute = int(minute)
                    
                    # 北京时间 + 1小时 = 目标网站时间
                    target_hour = hour + 1
                    if target_hour >= 24:
                        target_hour -= 24
                    
                    # 格式化为目标网站的时间格式
                    converted_time = f"{target_hour:02d}:{minute:02d}"
                    print(f"[时区转换] 转换后时间: {converted_time}")
                    return converted_time
            
            return match_time
        except Exception as e:
            print(f"[时区转换] 转换失败: {str(e)}")
            return ""
    
    async def _get_team_name_mapping(self) -> Dict[str, str]:
        """获取队名映射（中文到英文）"""
        return {
            '坦佩雷山猫': 'Ilves',
            '库普斯': 'KuPS',
            '哈德斯菲尔德': 'Huddersfield',
            '博尔顿': 'Bolton',
            # 可以根据需要添加更多映射
        }
    
    async def _find_match_row(self, driver, wait, home_en: str, away_en: str, home_team: str, away_team: str, target_time: str = "", league: str = ""):
        """查找匹配的比赛行 - 使用三层筛选逻辑"""
        try:
            print(f"[查找比赛行] 开始查找比赛行...")
            print(f"[查找比赛行] 目标队名: {home_en} vs {away_en}")
            print(f"[查找比赛行] 目标时间: {target_time}")
            
            # 获取页面中所有的表格行
            rows = driver.find_elements(By.TAG_NAME, "tr")
            print(f"[查找比赛行] 找到 {len(rows)} 行")
            
            for i, row in enumerate(rows):
                try:
                    row_text = row.text.lower()
                    print(f"[查找比赛行] 第{i+1}行内容: {row_text[:100]}...")
                    
                    # 第一层：时间匹配筛选
                    time_matched = False
                    if target_time and ":" in target_time:
                        # 检查行中是否包含目标时间
                        time_matched = target_time in row_text
                        print(f"[查找比赛行] 时间匹配: {time_matched} (目标: {target_time})")
                    
                    # 第二层：队名匹配筛选 - 更灵活的匹配策略
                    home_found = False
                    away_found = False
                    
                    # 检查主队名（支持部分匹配）
                    if home_en.lower() in row_text or home_team in row_text:
                        home_found = True
                    elif any(word in row_text for word in home_en.lower().split()):
                        home_found = True
                    
                    # 检查客队名（支持部分匹配）
                    if away_en.lower() in row_text or away_team in row_text:
                        away_found = True
                    elif any(word in row_text for word in away_en.lower().split()):
                        away_found = True
                    
                    team_matched = home_found and away_found
                    print(f"[查找比赛行] 队名匹配: {team_matched} (主队: {home_found}, 客队: {away_found})")
                    print(f"[查找比赛行] 行内容包含: {row_text[:200]}...")
                    print(f"[查找比赛行] 搜索队名: {home_en.lower()}, {away_en.lower()}")
                    
                    # 第三层：联赛类型验证
                    # 根据联赛类型设置匹配指示器
                    league_indicators = []
                    if '芬超' in home_team + away_team or '芬兰' in league:
                        league_indicators = ['finland', 'veikkausliiga', 'fin', 'finnish']
                    elif '英甲' in league or '英格兰' in league:
                        league_indicators = ['england', 'eng', 'uk']
                    elif '英超' in league:
                        league_indicators = ['england', 'eng', 'uk', 'premier']
                    
                    has_league_indicator = any(indicator in row_text for indicator in league_indicators)
                    
                    # 排除其他联赛的指示器
                    other_league_indicators = ['ukraine', 'brazil', 'bra', 'spain', 'spa', 'italy', 'ita', 'germany', 'ger', 'ucl']
                    has_other_league_indicator = any(indicator in row_text for indicator in other_league_indicators)
                    
                    # 联赛匹配逻辑：有目标联赛指示器且没有其他联赛指示器
                    league_matched = has_league_indicator and not has_other_league_indicator
                    print(f"[查找比赛行] 联赛匹配: {league_matched} (目标联赛: {has_league_indicator}, 其他联赛: {has_other_league_indicator})")
                    
                    # 三重匹配条件：满足其中两个条件即可
                    match_conditions = [time_matched, team_matched, league_matched]
                    satisfied_conditions = sum(match_conditions)
                    
                    print(f"[查找比赛行] 匹配条件满足情况: {satisfied_conditions}/3")
                    
                    if satisfied_conditions >= 2:
                        print(f"[查找比赛行] 找到匹配行: {row_text[:200]}...")
                        print(f"[查找比赛行] 匹配条件: 时间={time_matched}, 队名={team_matched}, 联赛={league_matched}")
                        return row
                    else:
                        print(f"[查找比赛行] 条件不满足，跳过此行")
                        continue
                        
                except Exception as e:
                    print(f"[查找比赛行] 处理第{i+1}行时出错: {e}")
                    continue
            
            print(f"[查找比赛行] 未找到匹配的比赛行")
            return None
            
        except Exception as e:
            print(f"[查找比赛行] 查找失败: {str(e)}")
            return None
    
    async def _click_stats_button_in_row(self, driver, wait, match_row):
        """在比赛行中点击stats按钮"""
        try:
            print(f"[点击Stats] 开始查找stats按钮...")
            
            # 获取当前URL
            current_url = driver.current_url
            print(f"[点击Stats] 点击前URL: {current_url}")
            
            # 在行内查找所有可能的按钮和链接
            all_buttons = match_row.find_elements(By.TAG_NAME, "a")
            print(f"[点击Stats] 找到 {len(all_buttons)} 个链接")
            
            # 优先查找stats相关按钮
            for i, button in enumerate(all_buttons):
                try:
                    button_text = button.text.lower().strip()
                    href = button.get_attribute('href')
                    print(f"[点击Stats] 按钮{i+1}: 文本='{button_text}', href='{href}'")
                    
                    # 查找stats、league stats等按钮
                    if any(keyword in button_text for keyword in ['stats', 'league stats', 'statistics']):
                        print(f"[点击Stats] 找到stats按钮: {button_text}")
                        
                        # 尝试多种点击方式
                        try:
                            # 滚动到按钮位置
                            driver.execute_script("arguments[0].scrollIntoView(true);", button)
                            time.sleep(1)
                            
                            # 方式1: 直接点击
                            button.click()
                            print(f"[点击Stats] 直接点击成功")
                        except Exception as e1:
                            print(f"[点击Stats] 直接点击失败: {e1}")
                            try:
                                # 方式2: JavaScript点击
                                driver.execute_script("arguments[0].click();", button)
                                print(f"[点击Stats] JavaScript点击成功")
                            except Exception as e2:
                                print(f"[点击Stats] JavaScript点击失败: {e2}")
                                continue
                        
                        # 等待页面跳转
                        time.sleep(5)
                        
                        # 检查URL是否改变
                        new_url = driver.current_url
                        print(f"[点击Stats] 点击后URL: {new_url}")
                        
                        if new_url != current_url:
                            print(f"[点击Stats] URL已改变，跳转成功")
                            return True
                        else:
                            print(f"[点击Stats] URL未改变，可能跳转失败")
                            
                except Exception as e:
                    print(f"[点击Stats] 处理stats链接{i+1}失败: {e}")
                    continue
            
            # 如果没有找到stats链接，尝试查找包含stats文本的链接
            all_links = match_row.find_elements(By.TAG_NAME, "a")
            print(f"[点击Stats] 查找所有链接，共找到 {len(all_links)} 个")
            
            for i, link in enumerate(all_links):
                try:
                    link_text = link.text.lower().strip()
                    href = link.get_attribute('href')
                    print(f"[点击Stats] 所有链接{i+1}: 文本='{link_text}', href='{href}'")
                    
                    if 'stats' in link_text or 'statistics' in link_text:
                        print(f"[点击Stats] 点击stats文本链接{i+1}: {link_text}")
                        
                        # 尝试点击
                        try:
                            link.click()
                            print(f"[点击Stats] 直接点击成功")
                        except Exception as e1:
                            print(f"[点击Stats] 直接点击失败: {e1}")
                            try:
                                driver.execute_script("arguments[0].click();", link)
                                print(f"[点击Stats] JavaScript点击成功")
                            except Exception as e2:
                                print(f"[点击Stats] JavaScript点击失败: {e2}")
                                continue
                        
                        time.sleep(5)
                        new_url = driver.current_url
                        print(f"[点击Stats] 点击后URL: {new_url}")
                        
                        if new_url != current_url:
                            print(f"[点击Stats] URL已改变，跳转成功")
                            return True
                        else:
                            print(f"[点击Stats] URL未改变，可能跳转失败")
                            
                except Exception as e:
                    print(f"[点击Stats] 处理所有链接{i+1}失败: {e}")
                    continue
            
            print(f"[点击Stats] 未找到有效的stats按钮")
            return False
            
        except Exception as e:
            print(f"[点击Stats] 点击stats按钮失败: {str(e)}")
            return False
    
    async def _click_analysis_button_in_row(self, driver, wait, match_row):
        """在比赛行中点击analysis按钮"""
        try:
            print(f"[点击Analysis] 开始查找analysis按钮...")
            
            # 在行内查找analysis相关的链接
            analysis_links = match_row.find_elements(By.CSS_SELECTOR, "a[href*='analysis']")
            if analysis_links:
                print(f"[点击Analysis] 找到 {len(analysis_links)} 个analysis链接")
                for link in analysis_links:
                    try:
                        link_text = link.text.lower()
                        if 'analysis' in link_text or 'anal' in link_text:
                            print(f"[点击Analysis] 点击analysis链接: {link_text}")
                            driver.execute_script("arguments[0].click();", link)
                            time.sleep(3)
                            return True
                    except Exception as e:
                        print(f"[点击Analysis] 点击analysis链接失败: {e}")
                        continue
            
            # 如果没有找到analysis链接，尝试查找包含analysis文本的链接
            all_links = match_row.find_elements(By.TAG_NAME, "a")
            for link in all_links:
                try:
                    link_text = link.text.lower()
                    if 'analysis' in link_text or 'anal' in link_text:
                        print(f"[点击Analysis] 点击analysis文本链接: {link_text}")
                        driver.execute_script("arguments[0].click();", link)
                        time.sleep(3)
                        return True
                except Exception as e:
                    print(f"[点击Analysis] 点击analysis文本链接失败: {e}")
                    continue
            
            print(f"[点击Analysis] 未找到analysis按钮")
            return False
            
        except Exception as e:
            print(f"[点击Analysis] 点击analysis按钮失败: {str(e)}")
            return False
    
    
    async def _search_and_navigate_to_match(self, driver, wait, site_name: str, match_info: Dict) -> bool:
        """
        搜索并导航到目标比赛页面
        
        Args:
            driver: WebDriver实例
            wait: WebDriverWait实例
            site_name: 网站名称
            match_info: 比赛信息
            
        Returns:
            是否成功导航到比赛页面
        """
        try:
            home_team = match_info.get('home_team', '')
            away_team = match_info.get('away_team', '')
            
            if not home_team or not away_team:
                print(f"[搜索] 比赛信息不完整，跳过搜索")
                return False
            
            print(f"[搜索] 开始搜索比赛: {home_team} vs {away_team}")
            
            # 根据网站类型使用不同的搜索策略
            if site_name == 'sofascore':
                return await self._search_sofascore_match(driver, wait, home_team, away_team)
            elif site_name == 'flashscore':
                return await self._search_flashscore_match(driver, wait, home_team, away_team)
            elif site_name == 'whoscored':
                return await self._search_whoscored_match(driver, wait, home_team, away_team)
            else:
                print(f"[搜索] 网站 {site_name} 暂不支持搜索功能")
                return False
                
        except Exception as e:
            print(f"[搜索] 搜索过程中发生异常: {str(e)}")
            return False
    
    async def _search_sofascore_match(self, driver, wait, home_team: str, away_team: str) -> bool:
        """在SofaScore中搜索比赛"""
        try:
            # 构建搜索词
            search_terms = [
                f"{home_team} vs {away_team}",
                home_team,
                away_team
            ]
            
            for search_term in search_terms:
                try:
                    print(f"[SofaScore搜索] 尝试搜索: {search_term}")
                    
                    # 查找搜索框
                    search_selectors = [
                        "input[placeholder*='Search']",
                        "input[type='search']",
                        ".search-input",
                        "#search"
                    ]
                    
                    search_box = None
                    for selector in search_selectors:
                        try:
                            search_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                            print(f"[SofaScore搜索] 找到搜索框: {selector}")
                            break
                        except TimeoutException:
                            continue
                    
                    if not search_box:
                        print(f"[SofaScore搜索] 未找到搜索框")
                        continue
                    
                    # 清空并输入搜索词
                    search_box.clear()
                    search_box.send_keys(search_term)
                    search_box.send_keys(Keys.RETURN)
                    
                    # 等待搜索结果加载
                    time.sleep(5)
                    
                    # 检查是否跳转到搜索结果页面
                    current_url = driver.current_url
                    if "search" in current_url.lower() or current_url != "https://www.sofascore.com/football":
                        print(f"[SofaScore搜索] 搜索成功，页面跳转到: {current_url}")
                        return True
                    
                except Exception as e:
                    print(f"[SofaScore搜索] 搜索词 '{search_term}' 失败: {str(e)}")
                    continue
            
            print(f"[SofaScore搜索] 所有搜索词都失败")
            return False
            
        except Exception as e:
            print(f"[SofaScore搜索] 搜索过程异常: {str(e)}")
            return False
    
    async def _search_flashscore_match(self, driver, wait, home_team: str, away_team: str) -> bool:
        """在FlashScore中搜索比赛"""
        try:
            print(f"[FlashScore搜索] 开始搜索: {home_team} vs {away_team}")
            
            # FlashScore的搜索策略 - 尝试直接URL构建或联赛导航
            # 这里可以实现更复杂的搜索逻辑
            
            # 暂时返回False，因为FlashScore的搜索比较复杂
            print(f"[FlashScore搜索] FlashScore搜索功能待实现")
            return False
            
        except Exception as e:
            print(f"[FlashScore搜索] 搜索过程异常: {str(e)}")
            return False
    
    async def _search_whoscored_match(self, driver, wait, home_team: str, away_team: str) -> bool:
        """在WhoScored中搜索比赛"""
        try:
            print(f"[WhoScored搜索] 开始搜索: {home_team} vs {away_team}")
            
            # WhoScored通常被Cloudflare拦截，搜索功能可能不可用
            print(f"[WhoScored搜索] WhoScored可能被反爬虫拦截，搜索功能不可用")
            return False
            
        except Exception as e:
            print(f"[WhoScored搜索] 搜索过程异常: {str(e)}")
            return False
    
    async def generate_screenshot(self, site_name: str, match_info: Dict = None, max_retries: int = 3) -> Dict:
        """
        生成体育数据网站截图
        
        Args:
            site_name: 网站名称 (flashscore, sofascore, whoscored, espn, bbc_sport)
            match_info: 比赛信息
            max_retries: 最大重试次数
            
        Returns:
            生成结果字典
        """
        if site_name not in self.supported_sites:
            return {
                "success": False,
                "message": f"不支持的网站: {site_name}",
                "timestamp": datetime.now().isoformat()
            }
        
        site_info = self.supported_sites[site_name]
        print(f"=== 开始生成 {site_info['name']} 截图 ===")
        print(f"目标URL: {site_info['url']}")
        
        # 首先清理可能存在的Chrome进程
        await self._cleanup_chrome_processes()
        
        for attempt in range(max_retries):
            driver = None
            try:
                print(f"[尝试 {attempt + 1}/{max_retries}] 正在生成截图...")
                driver = self._setup_driver()
                wait = WebDriverWait(driver, 30)
                
                # 访问网站
                print(f"[信息] 正在访问: {site_info['url']}")
                driver.get(site_info['url'])
                time.sleep(5) # 等待页面加载
                
                print(f"[信息] 页面标题: {driver.title}")
                print(f"[信息] 当前URL: {driver.current_url}")
                
                # 检查页面是否正常加载
                if not driver.title or len(driver.title) < 3:
                    print(f"[警告] 页面可能未正确加载")
                    raise WebDriverException("页面未正确加载或被反爬虫阻止")
                
                # 如果有比赛信息，尝试搜索目标比赛
                if match_info:
                    search_success = await self._search_and_navigate_to_match(driver, wait, site_name, match_info)
                    if search_success:
                        print(f"[成功] 成功搜索并导航到目标比赛页面")
                    else:
                        print(f"[警告] 搜索失败，将截图当前页面")
                
                # 等待页面内容完全加载
                time.sleep(3)
                
                # 生成截图文件名
                match_code = match_info.get('match_code', 'unknown') if match_info else 'general'
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_filename = f"screenshot_{match_code}_{site_name}_{timestamp}.png"
                screenshot_path = os.path.join(self.screenshot_dir, screenshot_filename)
                
                # 截图
                driver.save_screenshot(screenshot_path)
                
                # 验证截图文件
                if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 1000:
                    print(f"[成功] 截图生成成功: {screenshot_filename}")
                    print(f"[信息] 文件大小: {os.path.getsize(screenshot_path)} bytes")
                    
                    return {
                        "success": True,
                        "screenshot_path": screenshot_path,
                        "screenshot_filename": screenshot_filename,
                        "site_info": site_info,
                        "match_info": match_info,
                        "file_size": os.path.getsize(screenshot_path),
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    print(f"[失败] 截图文件无效或太小")
                    raise Exception("截图文件无效")
                    
            except (TimeoutException, WebDriverException) as e:
                print(f"[失败] 截图生成失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    print(f"[重试] 等待 {5 * (attempt + 1)} 秒后重试...")
                    time.sleep(5 * (attempt + 1))
                else:
                    print(f"[失败] 达到最大重试次数，放弃截图生成。")
                    return {
                        "success": False,
                        "message": f"截图生成失败: {str(e)}",
                        "site_info": site_info,
                        "attempts": max_retries,
                        "timestamp": datetime.now().isoformat()
                    }
            except Exception as e:
                print(f"[严重失败] 截图生成发生未知错误: {e}")
                return {
                    "success": False,
                    "message": f"截图生成异常: {str(e)}",
                    "site_info": site_info,
                    "timestamp": datetime.now().isoformat()
                }
            finally:
                if driver:
                    driver.quit()
                # 每次尝试后清理进程，确保干净的环境
                await self._cleanup_chrome_processes()
        
        return {
            "success": False,
            "message": "所有重试均失败",
            "site_info": site_info,
            "timestamp": datetime.now().isoformat()
        }
    
    async def generate_multiple_screenshots(self, site_names: List[str], match_info: Dict = None) -> List[Dict]:
        """
        批量生成多个网站的截图
        
        Args:
            site_names: 网站名称列表
            match_info: 比赛信息
            
        Returns:
            生成结果列表
        """
        print(f"=== 开始批量生成截图 ===")
        print(f"目标网站: {site_names}")
        
        results = []
        for site_name in site_names:
            if site_name in self.supported_sites:
                result = await self.generate_screenshot(site_name, match_info)
                results.append(result)
                
                # 避免过于频繁的请求
                time.sleep(2)
            else:
                results.append({
                    "success": False,
                    "message": f"不支持的网站: {site_name}",
                    "timestamp": datetime.now().isoformat()
                })
        
        # 统计结果
        success_count = sum(1 for r in results if r["success"])
        total_count = len(results)
        
        print(f"=== 批量截图生成完成 ===")
        print(f"总数量: {total_count}")
        print(f"成功: {success_count}")
        print(f"失败: {total_count - success_count}")
        
        return results
    
    async def generate_for_match(self, match_info: Dict) -> Dict:
        """
        为特定比赛生成专业体育数据网站截图
        
        Args:
            match_info: 比赛信息
            
        Returns:
            生成结果
        """
        match_code = match_info.get('match_code', 'unknown')
        print(f"=== 为比赛 {match_code} 生成截图 ===")
        
        # 按优先级排序的网站列表
        priority_sites = ["flashscore", "sofascore", "whoscored"]  # 高优先级网站
        
        results = await self.generate_multiple_screenshots(priority_sites, match_info)
        
        # 生成主截图文件（使用第一个成功的截图）
        main_screenshot = None
        for result in results:
            if result["success"]:
                main_screenshot = result["screenshot_path"]
                
                # 创建主截图文件
                main_filename = f"screenshot_{match_code}.png"
                main_path = os.path.join(self.screenshot_dir, main_filename)
                
                # 复制到主截图文件
                import shutil
                shutil.copy2(result["screenshot_path"], main_path)
                
                print(f"[成功] 主截图已保存: {main_filename}")
                break
        
        return {
            "success": len([r for r in results if r["success"]]) > 0,
            "match_code": match_code,
            "main_screenshot": main_screenshot,
            "all_results": results,
            "generated_count": len([r for r in results if r["success"]]),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_supported_sites(self) -> Dict:
        """获取支持的网站列表"""
        return self.supported_sites
    
    def list_generated_screenshots(self) -> List[str]:
        """列出已生成的截图文件"""
        if not os.path.exists(self.screenshot_dir):
            return []
        
        screenshot_files = []
        for filename in os.listdir(self.screenshot_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                screenshot_files.append(filename)
        
        return sorted(screenshot_files)

# 创建全局实例
sports_screenshot_generator = SportsScreenshotGenerator()
