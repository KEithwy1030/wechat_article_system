import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
from datetime import datetime, timedelta
import logging
import subprocess
import psutil

class SportteryResultsScraper:
    """竞彩官网赛果抓取器"""
    
    def __init__(self):
        self.base_url = "https://www.sporttery.cn/jc/zqsgkj/"
        self.logger = logging.getLogger(__name__)
        
    def _setup_driver(self):
        """设置Chrome驱动 - 优化版，增强反检测能力"""
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
        
        chrome_options = Options()
        
        # 基础设置
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # 性能优化
        chrome_options.add_argument('--disable-images')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--disable-features=VizDisplayCompositor')
        
        # 反检测设置
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--disable-automation')
        chrome_options.add_argument('--disable-infobars')
        chrome_options.add_argument('--disable-extensions-file-access-check')
        chrome_options.add_argument('--disable-extensions-http-throttling')
        
        # 网络设置
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-field-trial-config')
        
        # 用户代理 - 使用最新的Chrome版本
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
        
        # 实验性选项
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("detach", True)
        
        # 网络超时设置
        chrome_options.add_argument('--timeout=30000')
        chrome_options.add_argument('--page-load-timeout=30000')
        
        # 使用webdriver-manager自动下载并匹配Chrome版本
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 设置页面加载超时
        driver.set_page_load_timeout(30)
        driver.implicitly_wait(10)
        
        # 执行反检测脚本
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        return driver
    
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
            await asyncio.sleep(2)
        except Exception as e:
            print(f"[清理] 清理Chrome进程时出错: {e}")
    
    async def scrape_results(self, days_back=3, max_retries=3):
        """抓取赛果数据 - 增强版，支持重试机制
        
        Args:
            days_back: 抓取多少天前的赛果，默认3天
            max_retries: 最大重试次数，默认3次
        """
        print(f"=== 开始抓取竞彩官网赛果 ===")
        print(f"目标页面: {self.base_url}")
        print(f"最大重试次数: {max_retries}")
        
        # 首先清理可能存在的Chrome进程
        await self._cleanup_chrome_processes()
        
        for attempt in range(max_retries):
            driver = None
            try:
                print(f"\n[尝试 {attempt + 1}/{max_retries}] 初始化WebDriver...")
                driver = self._setup_driver()
                wait = WebDriverWait(driver, 20)
            
                print(f"[尝试 {attempt + 1}] 访问赛果页面...")
                driver.get(self.base_url)
                
                # 等待页面完全加载
                await asyncio.sleep(5)
                
                print(f"页面标题: {driver.title}")
                print(f"当前URL: {driver.current_url}")
                
                # 检查页面是否正常加载
                if "竞彩" not in driver.title and "sporttery" not in driver.current_url.lower():
                    raise Exception("页面加载异常，可能被反爬虫机制阻止")
                
                print(f"[尝试 {attempt + 1}] 设置日期范围...")
                await self._set_date_range(driver, days_back)
                
                print(f"[尝试 {attempt + 1}] 点击查询按钮...")
                await self._click_query_button(driver)
                
                # 等待结果加载
                await asyncio.sleep(5)
                
                print(f"[尝试 {attempt + 1}] 解析赛果数据...")
                results = await self._parse_results(driver)
                
                if results:
                    print(f"[成功] 成功抓取到 {len(results)} 条赛果数据")
                    return results
                else:
                    print(f"[警告] 尝试 {attempt + 1} 无结果")
                    if attempt < max_retries - 1:
                        print(f"等待 5 秒后重试...")
                        await asyncio.sleep(5)
                        continue
                    else:
                        print(f"[最终] 所有尝试均无结果，返回空数据")
                        return []
                    
            except Exception as e:
                print(f"[错误] 尝试 {attempt + 1} 失败: {e}")
                print(f"[错误] 错误类型: {type(e).__name__}")
                if attempt < max_retries - 1:
                    print(f"等待 10 秒后重试...")
                    await asyncio.sleep(10)
                    continue
                else:
                    print(f"[最终] 所有尝试均失败: {e}")
                    return []
            finally:
                if driver:
                    try:
                        driver.quit()
                        print(f"[清理] WebDriver 已关闭")
                    except:
                        pass
                
                # 清理Chrome进程
                await self._cleanup_chrome_processes()
        
        print(f"[失败] 抓取赛果失败，已尝试 {max_retries} 次")
        return []
    
    async def _set_date_range(self, driver, days_back):
        """设置日期范围"""
        try:
            # 计算日期范围 - 获取最近几天的真实赛果
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            start_date_str = start_date.strftime("%Y-%m-%d")
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            print(f"设置日期范围: {start_date_str} 至 {end_date_str}")
            
            # 等待页面完全加载
            time.sleep(3)
            
            # 简化日期设置 - 尝试直接访问带日期参数的URL
            current_url = driver.current_url
            if '?' in current_url:
                # 如果URL已有参数，添加日期参数
                date_params = f"&startDate={start_date_str}&endDate={end_date_str}"
                new_url = current_url + date_params
            else:
                # 如果URL没有参数，添加日期参数
                date_params = f"?startDate={start_date_str}&endDate={end_date_str}"
                new_url = current_url + date_params
            
            print(f"尝试访问带日期参数的URL: {new_url}")
            driver.get(new_url)
            time.sleep(3)
            
        except Exception as e:
            print(f"设置日期范围失败: {e}")
            # 尝试直接访问带参数的URL作为备选方案
            try:
                param_url = f"{self.base_url}?startDate={start_date_str}&endDate={end_date_str}"
                driver.get(param_url)
                time.sleep(5)
                print("使用URL参数方式设置日期")
            except Exception as e2:
                print(f"URL参数方式也失败: {e2}")
    
    async def _click_query_button(self, driver):
        """点击查询按钮"""
        try:
            # 等待页面加载
            time.sleep(3)
            
            # 尝试多种方式查找查询按钮（优先查找"开始查询"按钮）
            query_selectors = [
                "//button[contains(text(), '开始查询')]",
                "//button[contains(text(), '查询')]",
                "//button[contains(text(), '搜索')]",
                "//input[@type='submit']",
                "//button[@type='submit']",
                "//button[contains(@class, 'btn')]",
                "//button[contains(@class, 'query')]",
                "//button[contains(@class, 'search')]",
                "//button[contains(@id, 'query')]",
                "//button[contains(@id, 'search')]",
                "//a[contains(text(), '开始查询')]",
                "//a[contains(text(), '查询')]",
                "//a[contains(text(), '搜索')]"
            ]
            
            query_button = None
            for selector in query_selectors:
                try:
                    buttons = driver.find_elements(By.XPATH, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            query_button = button
                            print(f"找到查询按钮: {selector}")
                            break
                    if query_button:
                        break
                except:
                    continue
            
            if query_button:
                # 尝试点击
                try:
                    # 滚动到按钮位置
                    driver.execute_script("arguments[0].scrollIntoView(true);", query_button)
                    time.sleep(1)
                    
                    query_button.click()
                    print("点击查询按钮成功")
                    time.sleep(5)  # 等待结果加载
                except Exception as e:
                    # 如果普通点击失败，尝试JavaScript点击
                    driver.execute_script("arguments[0].click();", query_button)
                    print("使用JavaScript点击查询按钮成功")
                    time.sleep(5)
            else:
                print("未找到查询按钮，尝试直接提交表单")
                # 尝试直接提交表单
                try:
                    driver.execute_script("document.forms[0].submit();")
                    print("直接提交表单成功")
                    time.sleep(5)
                except:
                    print("表单提交也失败，继续解析当前页面")
                    
        except Exception as e:
            print(f"点击查询按钮失败: {e}")
            print("继续尝试解析当前页面内容")
    
    async def _parse_results(self, driver):
        """解析赛果数据（支持分页）"""
        all_results = []
        
        try:
            # 等待页面内容加载
            time.sleep(2)
            
            # 获取总页数
            total_pages = await self._get_total_pages(driver)
            print(f"发现总页数: {total_pages}")
            
            # 智能抓取：根据实际需要抓取赛果
            print(f"智能抓取：根据实际需要抓取赛果（已结束且在我们网站中的比赛）")
            
            # 获取我们需要抓取赛果的比赛列表
            needed_matches = await self._get_needed_matches()
            print(f"需要抓取赛果的比赛数量: {len(needed_matches)}")
            
            if not needed_matches:
                print("[成功] 没有需要抓取赛果的比赛，跳过抓取")
                return []
            
            # 根据需要的比赛数量智能判断抓取页数
            estimated_pages = min(total_pages, max(1, len(needed_matches) // 20 + 1))
            print(f"[目标] 智能判断：预计需要抓取 {estimated_pages} 页")
            
            for page_num in range(1, estimated_pages + 1):
                print(f"\n[抓取] 正在抓取第 {page_num} 页...")
                
                # 解析当前页面的数据
                page_results = await self._parse_current_page(driver)
                all_results.extend(page_results)
                print(f"[成功] 第 {page_num} 页抓取到 {len(page_results)} 条赛果")
                
                # 检查是否已经抓取到足够的赛果
                if len(all_results) >= len(needed_matches) * 2:  # 留一些余量
                    print(f"[目标] 已抓取到足够的赛果数据，停止抓取")
                    break
                
                # 如果不是最后一页，点击下一页
                if page_num < estimated_pages:
                    if not await self._go_to_next_page(driver, page_num + 1):
                        print(f"[警告] 无法跳转到第 {page_num + 1} 页，停止抓取")
                        break
                    time.sleep(3)  # 等待页面加载
            
            # 去重处理
            unique_results = []
            seen_matches = set()
            
            for result in all_results:
                match_key = f"{result.get('match_code', '')}_{result.get('home_team', '')}_{result.get('away_team', '')}"
                if match_key not in seen_matches:
                    seen_matches.add(match_key)
                    unique_results.append(result)
            
            print(f"\n🎉 分页抓取完成，总共抓取到 {len(all_results)} 条赛果，去重后 {len(unique_results)} 条")
            
            # 保存赛果到数据库
            await self._save_results_to_database(unique_results)
            
            # 更新命中率统计
            await self._update_hit_rate_stats(unique_results)
            
            return unique_results
            
        except Exception as e:
            print(f"[失败] 解析赛果数据失败: {e}")
            return all_results
    
    async def _get_total_pages(self, driver):
        """获取总页数"""
        try:
            # 查找分页控件
            pagination_selectors = [
                "//div[contains(@class, 'pagination')]",
                "//div[contains(@class, 'page')]",
                "//div[contains(@class, 'pager')]",
                "//div[contains(@id, 'page')]",
                "//div[contains(@id, 'pagination')]"
            ]
            
            for selector in pagination_selectors:
                try:
                    pagination = driver.find_element(By.XPATH, selector)
                    if pagination:
                        # 查找页码链接
                        page_links = pagination.find_elements(By.XPATH, ".//a[contains(@href, 'page') or contains(text(), '下十页') or contains(text(), '尾页')]")
                        
                        if page_links:
                            # 尝试点击"尾页"获取总页数
                            try:
                                last_page_link = pagination.find_element(By.XPATH, ".//a[contains(text(), '尾页')]")
                                if last_page_link:
                                    last_page_link.click()
                                    time.sleep(3)
                                    
                                    # 获取当前页码
                                    current_page = driver.find_element(By.XPATH, "//a[contains(@class, 'current') or contains(@class, 'active')]")
                                    total_pages = int(current_page.text)
                                    print(f"[成功] 通过尾页获取总页数: {total_pages}")
                                    return total_pages
                            except:
                                pass
                        
                        # 如果无法获取总页数，返回默认值
                        print("[警告] 无法获取总页数，使用默认值10")
                        return 10
                except:
                    continue
            
            print("[警告] 未找到分页控件，使用默认值10")
            return 10
            
        except Exception as e:
            print(f"[警告] 获取总页数失败: {e}，使用默认值10")
            return 10
    
    async def _parse_current_page(self, driver):
        """解析当前页面的赛果数据"""
        results = []
        
        try:
            # 尝试多种方式查找赛果数据
            data_selectors = [
                "//table",
                "//div[contains(@class, 'result')]",
                "//div[contains(@class, 'match')]",
                "//div[contains(@class, 'game')]",
                "//ul[contains(@class, 'list')]",
                "//div[contains(@class, 'content')]"
            ]
            
            all_tables = []
            for selector in data_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    all_tables.extend(elements)
                except:
                    continue
            
            for table_idx, table in enumerate(all_tables):
                # 获取所有行（tr或li）
                rows = []
                try:
                    rows.extend(table.find_elements(By.TAG_NAME, 'tr'))
                except:
                    pass
                try:
                    rows.extend(table.find_elements(By.TAG_NAME, 'li'))
                except:
                    pass
                try:
                    rows.extend(table.find_elements(By.TAG_NAME, 'div'))
                except:
                    pass
                
                for row_idx, row in enumerate(rows):
                    try:
                        # 获取单元格
                        cells = []
                        try:
                            cells.extend(row.find_elements(By.TAG_NAME, 'td'))
                        except:
                            pass
                        try:
                            cells.extend(row.find_elements(By.TAG_NAME, 'span'))
                        except:
                            pass
                        try:
                            cells.extend(row.find_elements(By.TAG_NAME, 'div'))
                        except:
                            pass
                        
                        if len(cells) < 3:  # 至少需要3列数据
                            continue
                        
                        # 解析比赛数据
                        match_data = self._parse_match_row(cells)
                        if match_data:
                            results.append(match_data)
                    
                    except Exception as e:
                        continue
            
            return results
            
        except Exception as e:
            print(f"[失败] 解析当前页面失败: {e}")
            return results
    
    async def _go_to_next_page(self, driver, page_num):
        """跳转到下一页"""
        try:
            # 查找分页控件
            pagination_selectors = [
                "//div[contains(@class, 'pagination')]",
                "//div[contains(@class, 'page')]",
                "//div[contains(@class, 'pager')]"
            ]
            
            for selector in pagination_selectors:
                try:
                    pagination = driver.find_element(By.XPATH, selector)
                    if pagination:
                        # 尝试点击指定页码
                        try:
                            page_link = pagination.find_element(By.XPATH, f".//a[text()='{page_num}']")
                            if page_link:
                                page_link.click()
                                time.sleep(2)
                                return True
                        except:
                            pass
                        
                        # 尝试点击"下一页"
                        try:
                            next_link = pagination.find_element(By.XPATH, ".//a[contains(text(), '下一页') or contains(text(), '下十页')]")
                            if next_link:
                                next_link.click()
                                time.sleep(2)
                                return True
                        except:
                            pass
                except:
                    continue
            
            return False
            
        except Exception as e:
            print(f"[警告] 跳转下一页失败: {e}")
            return False
    
    async def _parse_page_text(self, driver):
        """解析页面文本内容"""
        try:
            print("[查找] 尝试解析页面文本内容...")
            
            # 获取页面文本
            page_text = driver.page_source
            print(f"页面文本长度: {len(page_text)} 字符")
            
            # 查找包含比赛信息的文本模式
            import re
            
            # 比赛代码模式
            match_code_pattern = r'(周[一二三四五六日]\d{3})'
            match_codes = re.findall(match_code_pattern, page_text)
            print(f"找到 {len(match_codes)} 个比赛代码")
            
            # 比分模式
            score_pattern = r'(\d+:\d+)'
            scores = re.findall(score_pattern, page_text)
            print(f"找到 {len(scores)} 个比分")
            
            # 队名模式
            team_pattern = r'([\u4e00-\u9fff]+(?:\([^)]*\))?)\s*VS\s*([\u4e00-\u9fff]+(?:\([^)]*\))?)'
            teams = re.findall(team_pattern, page_text)
            print(f"找到 {len(teams)} 个队名对")
            
            # 组合数据
            results = []
            for i, match_code in enumerate(match_codes):
                if i < len(teams) and i < len(scores):
                    home_team, away_team = teams[i]
                    score = scores[i]
                    
                    result = {
                        'match_code': match_code,
                        'home_team': home_team,
                        'away_team': away_team,
                        'full_score': score,
                        'status': '已完成',
                        'scraped_at': datetime.now().isoformat()
                    }
                    results.append(result)
                    print(f"[成功] 文本解析比赛: {match_code} - {home_team} VS {away_team} - {score}")
            
            return results
            
        except Exception as e:
            print(f"[失败] 解析页面文本失败: {e}")
            return []
    
    def _parse_match_row(self, cells):
        """解析单行比赛数据"""
        try:
            if len(cells) < 6:
                return None
            
            # 提取基本信息
            match_data = {
                'match_date': cells[0].text.strip() if len(cells) > 0 else '',
                'match_code': cells[1].text.strip() if len(cells) > 1 else '',
                'league': cells[2].text.strip() if len(cells) > 2 else '',
                'teams': cells[3].text.strip() if len(cells) > 3 else '',
                'half_score': cells[4].text.strip() if len(cells) > 4 else '',
                'full_score': cells[5].text.strip() if len(cells) > 5 else '',
                'status': cells[9].text.strip() if len(cells) > 9 else '',
                'scraped_at': datetime.now().isoformat()
            }
            
            # 解析对阵双方
            teams_text = match_data['teams']
            
            # 处理各种VS格式
            if ' VS ' in teams_text:
                # 标准格式：主队 VS 客队
                parts = teams_text.split(' VS ')
                match_data['home_team'] = parts[0].strip()
                match_data['away_team'] = parts[1].strip()
            elif 'VS' in teams_text:
                # 无空格格式：主队VS客队
                parts = teams_text.split('VS')
                if len(parts) == 2:
                    match_data['home_team'] = parts[0].strip()
                    match_data['away_team'] = parts[1].strip()
                else:
                    match_data['home_team'] = teams_text
                    match_data['away_team'] = ''
            else:
                match_data['home_team'] = teams_text
                match_data['away_team'] = ''
            
            # 清理队名：移除括号内容（如让球信息）
            if match_data['home_team']:
                # 移除括号及其内容
                import re
                match_data['home_team'] = re.sub(r'\([^)]*\)', '', match_data['home_team']).strip()
            if match_data['away_team']:
                match_data['away_team'] = re.sub(r'\([^)]*\)', '', match_data['away_team']).strip()
            
            # 验证数据完整性
            if not match_data['match_code'] or not match_data['full_score']:
                return None
            
            # 只返回已完成的比赛
            if match_data['status'] != '已完成':
                return None
            
            return match_data
            
        except Exception as e:
            print(f"[警告] 解析比赛行失败: {e}")
            return None

    async def _get_needed_matches(self):
        """获取需要抓取赛果的比赛列表"""
        try:
            import sqlite3
            from datetime import datetime, timedelta
            
            # 连接数据库
            conn = sqlite3.connect("system.db")
            cursor = conn.cursor()
            
            # 查询需要抓取赛果的比赛：官方赛程与历史赛程中缺少赛果的比赛都要抓
            cursor.execute("""
                SELECT m.match_code, m.home_team, m.away_team, m.league, m.match_time
                FROM lottery_matches m
                LEFT JOIN lottery_results mr ON m.match_code = mr.match_code
                WHERE (mr.full_score IS NULL OR mr.full_score = '')
                ORDER BY m.match_time DESC
            """)
            
            needed_matches = cursor.fetchall()
            conn.close()
            
            return needed_matches
            
        except Exception as e:
            print(f"[警告] 获取需要抓取赛果的比赛失败: {e}")
            return []
    
    async def _save_results_to_database(self, results):
        """保存赛果到数据库 - 改进匹配逻辑"""
        try:
            import sqlite3
            import re
            from datetime import datetime
            
            conn = sqlite3.connect("system.db")
            cursor = conn.cursor()
            
            # 获取数据库中的比赛数据
            cursor.execute('''
                SELECT match_code, home_team, away_team, league, match_time
                FROM lottery_matches 
                WHERE match_time >= date('now', '-7 days')
                ORDER BY match_time DESC
            ''')
            
            db_matches = cursor.fetchall()
            print(f"[列表] 数据库中有 {len(db_matches)} 场比赛需要匹配")
            
            def clean_team_name(name):
                """清理队名"""
                if not name:
                    return ""
                # 移除括号内容，如 "拜仁(-3)" -> "拜仁"
                name = re.sub(r'\([^)]*\)', '', name)
                # 移除特殊字符，但保留中文字符和字母
                name = re.sub(r'[^\u4e00-\u9fffA-Za-z0-9\s]', '', name)
                return name.strip()
            
            def find_match_by_teams(scraped_result, db_matches):
                """通过队伍名称匹配比赛"""
                scraped_home = clean_team_name(scraped_result.get('home_team', ''))
                scraped_away = clean_team_name(scraped_result.get('away_team', ''))
                scraped_league = scraped_result.get('league', '').strip()
                
                for db_match in db_matches:
                    db_code, db_home, db_away, db_league, db_time = db_match
                    db_home = clean_team_name(db_home)
                    db_away = clean_team_name(db_away)
                    db_league = db_league.strip()
                    
                    # 队伍名称匹配（包含关系）
                    home_match = (scraped_home in db_home or db_home in scraped_home) and len(scraped_home) > 1 and len(db_home) > 1
                    away_match = (scraped_away in db_away or db_away in scraped_away) and len(scraped_away) > 1 and len(db_away) > 1
                    
                    # 联赛匹配（可选）
                    league_match = True
                    if scraped_league and db_league:
                        league_match = scraped_league in db_league or db_league in scraped_league
                    
                    if home_match and away_match and league_match:
                        return db_code
                    elif home_match and away_match:
                        return db_code
                
                return None
            
            saved_count = 0
            matched_count = 0
            
            for result in results:
                match_code = result.get('match_code', '')
                home_team = result.get('home_team', '')
                away_team = result.get('away_team', '')
                full_score = result.get('full_score', '')
                half_score = result.get('half_score', '')
                status = result.get('status', '已完成')
                
                if not full_score:
                    continue
                
                # 首先尝试通过比赛代码匹配
                found_match_code = None
                if match_code:
                    cursor.execute('SELECT match_code FROM lottery_matches WHERE match_code = ?', (match_code,))
                    if cursor.fetchone():
                        found_match_code = match_code
                
                # 如果比赛代码匹配失败，尝试通过队伍名称匹配
                if not found_match_code:
                    found_match_code = find_match_by_teams(result, db_matches)
                
                if found_match_code:
                    matched_count += 1
                    
                    # 检查是否已存在赛果
                    cursor.execute('SELECT id FROM lottery_results WHERE match_code = ?', (found_match_code,))
                    existing = cursor.fetchone()
                    
                    if not existing:
                        # 插入新记录
                        cursor.execute('''
                            INSERT INTO lottery_results 
                            (match_code, home_team, away_team, half_score, full_score, status, source, scraped_at, created_at, updated_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            found_match_code,
                            home_team,
                            away_team,
                            half_score,
                            full_score,
                            status,
                            'sporttery_improved',
                            result.get('scraped_at', datetime.now().isoformat()),
                            datetime.now().isoformat(),
                            datetime.now().isoformat()
                        ))
                        saved_count += 1
                        print(f"[成功] 保存赛果: {found_match_code} - {home_team} vs {away_team} - {full_score}")
                    else:
                        print(f"[跳过] 跳过: {found_match_code} - 赛果已存在")
                else:
                    print(f"[失败] 未匹配: {home_team} vs {away_team} - {full_score}")
            
            conn.commit()
            conn.close()
            
            print(f"🎉 匹配完成: 成功匹配 {matched_count} 条，新保存 {saved_count} 条赛果到数据库")
            
        except Exception as e:
            print(f"[失败] 保存赛果到数据库失败: {e}")
    
    async def _update_hit_rate_stats(self, results):
        """更新命中率统计（基于分组完成状态）"""
        try:
            from services.lottery.prediction_manager import prediction_manager

            triggered_groups = set()
            processed_matches = 0
            for result in results:
                match_code = result.get('match_code', '')
                full_score = result.get('full_score', '')

                if match_code and full_score:
                    processed_matches += 1
                    update_info = prediction_manager.update_match_result_in_schedule(
                        match_code,
                        full_score,
                        result.get('half_score')
                    )
                    if update_info.get('group_completed'):
                        triggered_groups.add(update_info.get('group_date'))

            print(f"[目标] 命中率检查完成，共处理 {processed_matches} 场比赛，触发分组 {len(triggered_groups)} 个")

        except Exception as e:
            print(f"[失败] 更新命中率统计失败: {e}")
    
    async def _generate_mock_results(self):
        """生成模拟赛果数据用于测试"""
        try:
            print("[模拟] 开始生成模拟赛果数据...")
            
            # 获取数据库中的比赛数据
            import sqlite3
            conn = sqlite3.connect("system.db")
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT match_code, home_team, away_team, league, match_time
                FROM lottery_matches 
                WHERE match_time >= date('now', '-7 days')
                ORDER BY match_time DESC
            ''')
            
            db_matches = cursor.fetchall()
            conn.close()
            
            if not db_matches:
                print("[模拟] 数据库中没有比赛数据，生成默认模拟数据")
                return [
                    {
                        'match_code': '周一001',
                        'home_team': '曼城',
                        'away_team': '阿森纳',
                        'league': '英超',
                        'full_score': '2:1',
                        'half_score': '1:0',
                        'status': '已完成',
                        'scraped_at': datetime.now().isoformat()
                    },
                    {
                        'match_code': '周一002',
                        'home_team': '拜仁慕尼黑',
                        'away_team': '多特蒙德',
                        'league': '德甲',
                        'full_score': '3:2',
                        'half_score': '2:1',
                        'status': '已完成',
                        'scraped_at': datetime.now().isoformat()
                    }
                ]
            
            # 为数据库中的比赛生成模拟赛果
            mock_results = []
            import random
            
            for match in db_matches:
                match_code, home_team, away_team, league, match_time = match
                
                # 生成随机比分
                home_score = random.randint(0, 4)
                away_score = random.randint(0, 4)
                
                # 生成半场比分（通常比全场比分小）
                half_home = random.randint(0, min(home_score, 2))
                half_away = random.randint(0, min(away_score, 2))
                
                result = {
                    'match_code': match_code,
                    'home_team': home_team,
                    'away_team': away_team,
                    'league': league,
                    'full_score': f"{home_score}:{away_score}",
                    'half_score': f"{half_home}:{half_away}",
                    'status': '已完成',
                    'scraped_at': datetime.now().isoformat()
                }
                mock_results.append(result)
                
                print(f"[模拟] 生成赛果: {match_code} - {home_team} vs {away_team} - {home_score}:{away_score}")
            
            print(f"[模拟] 成功生成 {len(mock_results)} 条模拟赛果数据")
            
            # 保存模拟数据到数据库
            if mock_results:
                await self._save_results_to_database(mock_results)
            
            return mock_results
            
        except Exception as e:
            print(f"[失败] 生成模拟数据失败: {e}")
            return []

# 测试函数
async def test_scraper():
    """测试赛果抓取器"""
    scraper = SportteryResultsScraper()
    results = await scraper.scrape_results(days_back=2)
    
    print(f"\n=== 抓取结果汇总 ===")
    print(f"总共抓取到 {len(results)} 条赛果")
    
    for i, result in enumerate(results[:5]):  # 显示前5条
        print(f"\n赛果 {i+1}:")
        print(f"  比赛编号: {result.get('match_code', 'N/A')}")
        print(f"  联赛: {result.get('league', 'N/A')}")
        print(f"  对阵: {result.get('home_team', '')} VS {result.get('away_team', '')}")
        print(f"  半场比分: {result.get('half_score', 'N/A')}")
        print(f"  全场比分: {result.get('full_score', 'N/A')}")
        print(f"  状态: {result.get('status', 'N/A')}")

if __name__ == "__main__":
    asyncio.run(test_scraper())
