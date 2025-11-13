"""
竞彩网数据抓取器 - WechatBOT版本
从ai_content_system迁移，适配WechatBOT系统
"""
import asyncio
import re
import sys
import logging
from typing import List, Dict, Optional
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# 配置日志
logger = logging.getLogger(__name__)

class LotteryScraper:
    """竞彩网数据抓取器"""
    
    def __init__(self):
        self.base_url = 'https://www.sporttery.cn/jc/zqszsc/'
        self.driver = None
        self.wait = None
        logger.info("竞彩数据抓取器初始化")
    
    def _setup_driver(self):
        """设置Chrome浏览器驱动（性能优化版）"""
        try:
            chrome_options = Options()
            
            # 基础设置
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # 性能优化设置
            chrome_options.add_argument('--disable-images')  # 禁用图片加载
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            
            # 内存优化
            chrome_options.add_argument('--memory-pressure-off')
            chrome_options.add_argument('--max_old_space_size=4096')
            
            # 网络优化
            chrome_options.add_argument('--aggressive-cache-discard')
            chrome_options.add_argument('--disable-background-networking')
            
            # 反检测设置
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # 指定ChromeDriver路径（项目本地）
            import os
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            chromedriver_path = os.path.join(project_root, 'drivers', 'chromedriver.exe')
            
            # 如果本地没有，使用webdriver-manager自动下载
            if os.path.exists(chromedriver_path):
                service = Service(chromedriver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                # 使用webdriver-manager自动下载并匹配Chrome版本
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 反检测脚本
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # 设置超时时间
            self.driver.set_page_load_timeout(10)
            self.driver.implicitly_wait(3)
            
            # 设置等待时间
            self.wait = WebDriverWait(self.driver, 8)
            
            # 禁用图片和CSS加载以提升速度
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            # 设置网络条件
            self.driver.execute_cdp_cmd('Network.emulateNetworkConditions', {
                'offline': False,
                'downloadThroughput': 10 * 1024 * 1024,  # 10MB/s
                'uploadThroughput': 5 * 1024 * 1024,     # 5MB/s
                'latency': 10  # 10ms延迟
            })
            
            logger.info('Chrome浏览器驱动初始化成功')
            return True
            
        except Exception as e:
            logger.error(f'Chrome浏览器驱动初始化失败: {str(e)}')
            return False
    
    async def fetch_schedule(self, interrupt_check=None) -> Dict:
        """抓取竞彩赛程数据
        
        Args:
            interrupt_check: 中断检查函数，如果返回True则应该中断任务
        """
        logger.info('开始抓取竞彩网赛程数据')
        
        def check_interrupt():
            if interrupt_check and interrupt_check():
                logger.info('检测到中断信号，正在停止抓取任务')
                raise Exception("任务被中断")
        
        try:
            check_interrupt()
            
            if not self._setup_driver():
                return {
                    'matches': [],
                    'error': '浏览器驱动初始化失败',
                    'success': False
                }
            
            check_interrupt()
            
            # 访问网站
            self.driver.get(self.base_url)
            logger.info(f'正在访问: {self.base_url}')
            
            # 等待页面加载
            await asyncio.sleep(3)
            check_interrupt()
            
            # 等待赛程容器加载
            try:
                schedule_element = self.wait.until(
                    EC.presence_of_element_located((By.ID, "szsc_993"))
                )
                check_interrupt()
                
                # 等待内容加载
                await asyncio.sleep(5)
                check_interrupt()
                
                # 滚动页面触发更多内容加载
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                await asyncio.sleep(2)
                check_interrupt()
                
                # 提取比赛数据，传递中断检查函数
                all_matches = await self._extract_matches(interrupt_check)
                check_interrupt()
                
                logger.info(f'成功抓取 {len(all_matches)} 场比赛')
                
                return {
                    'matches': all_matches,
                    'total_count': len(all_matches),
                    'source': 'sporttery_official',
                    'scraped_at': datetime.now().isoformat(),
                    'success': True
                }
                
            except TimeoutException:
                logger.error('赛程容器加载超时')
                return {
                    'matches': [],
                    'error': '赛程容器加载超时',
                    'success': False
                }
                
        except Exception as e:
            logger.error(f'抓取赛程数据失败: {str(e)}')
            return {
                'matches': [],
                'error': str(e),
                'success': False
            }
            
        finally:
            if self.driver:
                self.driver.quit()
    
    async def _extract_matches(self, interrupt_check=None) -> List[Dict]:
        """提取比赛数据"""
        matches = []
        
        def check_interrupt():
            if interrupt_check and interrupt_check():
                logger.info('在数据提取过程中检测到中断信号')
                raise Exception("任务被中断")
        
        try:
            # 获取赛程容器的完整文本
            schedule_element = self.driver.find_element(By.ID, "szsc_993")
            full_text = schedule_element.text
            
            logger.info(f'赛程容器文本长度: {len(full_text)}')
            check_interrupt()
            
            # 解析文本，传递中断检查函数
            matches = self._parse_schedule_text(full_text, interrupt_check)
            check_interrupt()
            
            return matches
            
        except Exception as e:
            logger.error(f'提取比赛数据失败: {str(e)}')
            return []
    
    def _parse_schedule_text(self, text: str, interrupt_check=None) -> List[Dict]:
        """解析赛程文本"""
        matches = []
        
        def check_interrupt():
            if interrupt_check and interrupt_check():
                logger.info('在文本解析过程中检测到中断信号')
                raise Exception("任务被中断")
        
        try:
            check_interrupt()

            group_header_pattern = re.compile(
                r'(周[一二三四五六日])\s+(\d{4}-\d{2}-\d{2})\s+共\d+场比赛\s*\(比赛编号日期：(\d{6})\)',
                re.MULTILINE
            )
            headers = list(group_header_pattern.finditer(text))

            if not headers:
                raise ValueError("未能在赛程文本中找到任何分组标题，无法解析下注日期")

            match_pattern = re.compile(
                r'(周[一二三四五六日]\d{3})\s+([^\n]*?)\s+(\S+VS\S+)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})'
            )

            for index, header in enumerate(headers):
                check_interrupt()

                day_name = header.group(1)
                group_date = header.group(2)

                group_start = header.end()
                group_end = headers[index + 1].start() if index + 1 < len(headers) else len(text)
                group_text = text[group_start:group_end]

                group_matches = match_pattern.findall(group_text)

                if not group_matches:
                    logger.warning(f'分组 {day_name} {group_date} 未解析出任何比赛，可能是页面结构变化')

                for i, segment in enumerate(group_matches):
                    if i % 10 == 0 and i > 0:
                        check_interrupt()

                    match_code, league, teams_vs, match_time = segment
                    league = league.strip()
                    teams_vs = teams_vs.strip()
                    match_time = match_time.strip()

                    team_match = re.search(r'(\S+)VS(\S+)', teams_vs)
                    if not team_match:
                        logger.error(f'比赛 {match_code} 缺少队伍信息，文本内容: {teams_vs}')
                        continue

                    home_team = team_match.group(1).strip()
                    away_team = team_match.group(2).strip()

                    if not group_date:
                        raise ValueError(f'分组 {day_name} 缺少下注日期，解析结果无效')

                    match_data = {
                        'match_code': match_code,
                        'day': match_code[:2],
                        'home_team': home_team,
                        'away_team': away_team,
                        'match_time': match_time,
                        'league': league,
                        'match_display': f'{home_team} vs {away_team}',
                        'source': 'sporttery_official',
                        'scraped_at': datetime.now().isoformat(),
                        'status': 'pending',
                        'group_date': group_date
                    }

                    matches.append(match_data)
                    logger.info(f'解析比赛: {match_code} {home_team} vs {away_team} (分组日期: {group_date})')

            if not matches:
                raise ValueError("赛程文本解析完成，但未识别出任何比赛数据")

            logger.info(f'解析完成，共 {len(matches)} 场比赛')

        except Exception as e:
            logger.error(f'解析赛程失败: {str(e)}')
        
        return matches
    
    async def fetch_results(self, days_back: int = 7) -> Dict:
        """抓取比赛结果"""
        logger.info(f'开始抓取近{days_back}天的比赛结果')
        
        try:
            if not self._setup_driver():
                return {
                    'results': [],
                    'error': '浏览器驱动初始化失败',
                    'success': False
                }
            
            # 访问赛果页面（不是赛程页面）
            results_url = 'https://www.sporttery.cn/jc/zqsgkj/'
            self.driver.get(results_url)
            logger.info(f'正在访问赛果页面: {results_url}')
            await asyncio.sleep(3)
            
            # 等待页面加载（赛果页面可能使用不同的元素，尝试多种选择器）
            try:
                # 尝试等待赛果页面的常见元素
                self.wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
            except:
                # 如果找不到table，至少等待页面加载
                await asyncio.sleep(5)
            
            await asyncio.sleep(3)
            
            # 提取赛果（需要适配赛果页面的结构）
            results = await self._extract_results()
            
            logger.info(f'成功抓取 {len(results)} 个赛果')
            
            return {
                'results': results,
                'total_count': len(results),
                'source': 'sporttery_official',
                'scraped_at': datetime.now().isoformat(),
                'success': True
            }
            
        except Exception as e:
            logger.error(f'抓取赛果失败: {str(e)}')
            return {
                'results': [],
                'error': str(e),
                'success': False
            }
            
        finally:
            if self.driver:
                self.driver.quit()
    
    async def _extract_results(self, target_match_codes: List[str] = None) -> List[Dict]:
        """
        提取比赛结果（适配赛果页面结构）
        
        Args:
            target_match_codes: 目标比赛编号列表，如果提供则只抓取这些编号的赛果
        
        Returns:
            赛果数据列表
        """
        results = []
        found_codes = set()  # 记录已找到的match_code
        
        try:
            # 方法1：精确查找比分元素（用户提供的格式）
            # 查找 <span class="u-org">1:4</span> 或 <td width="60">1:4</td>
            try:
                # 查找所有包含比分的span元素（class="u-org"）
                score_spans = self.driver.find_elements(By.CSS_SELECTOR, 'span.u-org')
                logger.info(f'找到 {len(score_spans)} 个u-org span元素')
                
                # 查找所有包含比分的td元素（width="60"）
                score_tds = self.driver.find_elements(By.XPATH, '//td[@width="60"]')
                logger.info(f'找到 {len(score_tds)} 个width="60"的td元素')
                
                # 合并所有比分元素
                all_score_elements = list(score_spans) + list(score_tds)
                
                if all_score_elements:
                    # 从每个比分元素向上查找对应的比赛信息
                    for score_elem in all_score_elements:
                        try:
                            score_text = score_elem.text.strip()
                            # 验证是否是比分格式（如 "1:4"）
                            if ':' in score_text and score_text.count(':') == 1:
                                parts = score_text.split(':')
                                if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                                    # 找到比分，向上查找比赛信息
                                    try:
                                        row = score_elem.find_element(By.XPATH, './ancestor::tr')
                                        if row:
                                            cells = row.find_elements(By.TAG_NAME, "td")
                                            logger.debug(f'找到行，包含 {len(cells)} 个单元格')
                                            
                                            # 提取比赛信息
                                            match_code = None
                                            home_team = None
                                            away_team = None
                                            
                                            # 打印所有单元格内容用于调试
                                            cell_texts = [cell.text.strip() for cell in cells]
                                            logger.debug(f'单元格内容: {cell_texts}')
                                            
                                            # 方法1：从所有单元格中查找比赛编号（包含"周"和数字）
                                            for cell in cells:
                                                cell_text = cell.text.strip()
                                                if '周' in cell_text and any(c.isdigit() for c in cell_text):
                                                    # 提取完整的比赛编号（如"周一001"）
                                                    match = re.search(r'周[一二三四五六日]\d{3}', cell_text)
                                                    if match:
                                                        match_code = match.group(0)
                                                        logger.debug(f'找到比赛编号: {match_code}')
                                                        break
                                            
                                            # 方法2：如果没找到，尝试从第一个单元格提取
                                            if not match_code and len(cells) > 0:
                                                first_cell_text = cells[0].text.strip()
                                                match = re.search(r'周[一二三四五六日]\d{3}', first_cell_text)
                                                if match:
                                                    match_code = match.group(0)
                                                    logger.debug(f'从第一个单元格找到比赛编号: {match_code}')
                                            
                                            # 提取联赛信息
                                            league = None
                                            # 方法1：查找 <div class="league-bg"> 元素
                                            try:
                                                league_divs = row.find_elements(By.CSS_SELECTOR, 'div.league-bg')
                                                if league_divs:
                                                    league = league_divs[0].text.strip()
                                                    logger.debug(f'从league-bg div找到联赛: {league}')
                                            except Exception as e:
                                                logger.debug(f'查找league-bg div失败: {e}')
                                            
                                            # 方法2：如果方法1失败，查找包含联赛名称的td元素
                                            if not league:
                                                for cell in cells:
                                                    cell_text = cell.text.strip()
                                                    # 跳过比赛编号、比分、VS单元格
                                                    if '周' in cell_text or ':' in cell_text or 'VS' in cell_text.upper() or 'vs' in cell_text:
                                                        continue
                                                    # 联赛名称通常是较短的文本，且不包含数字和特殊符号
                                                    if cell_text and len(cell_text) < 20 and not re.search(r'\d+', cell_text):
                                                        # 检查是否是常见的联赛名称（包含中文字符）
                                                        if re.search(r'[\u4e00-\u9fa5]', cell_text):
                                                            league = cell_text
                                                            logger.debug(f'从td元素找到联赛: {league}')
                                                            break
                                            
                                            # 提取队伍信息：优先查找包含"VS"或"vs"的单元格
                                            for i, cell in enumerate(cells):
                                                cell_text = cell.text.strip()
                                                # 跳过比赛编号、比分、联赛的单元格
                                                if '周' in cell_text or ':' in cell_text or (league and cell_text == league):
                                                    continue
                                                
                                                # 查找包含VS或vs的单元格（这是最可靠的方式）
                                                if 'VS' in cell_text.upper() or 'vs' in cell_text:
                                                    # 分离主队和客队
                                                    parts_teams = re.split(r'\s*(?:VS|vs)\s*', cell_text, 1)
                                                    if len(parts_teams) >= 2:
                                                        home_team = parts_teams[0].strip()
                                                        away_team = parts_teams[1].strip()
                                                        # 清理队名（移除括号内容，如"(+1)"、"(-1)"等）
                                                        home_team = re.sub(r'\([^)]*\)', '', home_team).strip()
                                                        away_team = re.sub(r'\([^)]*\)', '', away_team).strip()
                                                        logger.debug(f'从VS单元格找到队伍: {home_team} vs {away_team}')
                                                        break
                                            
                                            # 如果找到比赛编号和比分，就保存
                                            if match_code:
                                                # 如果指定了目标match_code列表，只保存目标编号的赛果
                                                if target_match_codes and match_code not in target_match_codes:
                                                    continue
                                                
                                                home_score, away_score = parts[0], parts[1]
                                                result = {
                                                    'match_code': match_code,
                                                    'home_team': home_team or '',
                                                    'away_team': away_team or '',
                                                    'home_score': int(home_score),
                                                    'away_score': int(away_score),
                                                    'full_score': score_text,
                                                    'league': league or '',  # 添加联赛字段
                                                    'status': 'finished',
                                                    'source': 'sporttery_official',
                                                    'fetched_at': datetime.now().isoformat()
                                                }
                                                results.append(result)
                                                found_codes.add(match_code)
                                                logger.info(f'提取赛果: {match_code} {home_team or ""} {score_text} {away_team or ""}')
                                            else:
                                                logger.warning(f'找到比分 {score_text}，但未找到比赛编号')
                                    except Exception as e:
                                        logger.warning(f'从比分元素提取比赛信息失败: {e}')
                                        continue
                        except Exception as e:
                            logger.debug(f'处理比分元素失败: {e}')
                            continue
                            
            except Exception as e:
                logger.warning(f'精确查找比分元素失败: {e}')
            
            # 方法2：如果精确查找失败，尝试从表格中提取
            if not results:
                try:
                    tables = self.driver.find_elements(By.TAG_NAME, "table")
                    if tables:
                        for table in tables:
                            rows = table.find_elements(By.TAG_NAME, "tr")
                            for row in rows:
                                cells = row.find_elements(By.TAG_NAME, "td")
                                if len(cells) >= 5:  # 至少需要5列数据
                                    try:
                                        # 尝试提取比赛编号、队伍、比分等信息
                                        match_code_cell = cells[0].text.strip()
                                        if '周' in match_code_cell and any(c.isdigit() for c in match_code_cell):
                                            # 提取比分
                                            score_text = ""
                                            for cell in cells:
                                                text = cell.text.strip()
                                                if ':' in text and any(c.isdigit() for c in text):
                                                    score_text = text
                                                    break
                                            
                                            if score_text and ':' in score_text:
                                                home_score, away_score = score_text.split(':')
                                                
                                                # 提取联赛信息
                                                league = None
                                                # 方法1：查找 <div class="league-bg"> 元素
                                                try:
                                                    league_divs = row.find_elements(By.CSS_SELECTOR, 'div.league-bg')
                                                    if league_divs:
                                                        league = league_divs[0].text.strip()
                                                except:
                                                    pass
                                                
                                                # 方法2：如果方法1失败，从表格单元格中查找联赛
                                                if not league:
                                                    for cell in cells:
                                                        cell_text = cell.text.strip()
                                                        # 跳过比赛编号、比分、队伍名称
                                                        if '周' in cell_text or ':' in cell_text or 'VS' in cell_text.upper() or 'vs' in cell_text:
                                                            continue
                                                        # 联赛名称通常是较短的文本，且不包含数字
                                                        if cell_text and len(cell_text) < 20 and not re.search(r'\d+', cell_text):
                                                            if re.search(r'[\u4e00-\u9fa5]', cell_text):
                                                                league = cell_text
                                                                break
                                                
                                                # 如果指定了目标match_code列表，只保存目标编号的赛果
                                                if target_match_codes and match_code_cell not in target_match_codes:
                                                    continue
                                                
                                                result = {
                                                    'match_code': match_code_cell,
                                                    'home_team': cells[1].text.strip() if len(cells) > 1 else '',
                                                    'away_team': cells[2].text.strip() if len(cells) > 2 else '',
                                                    'home_score': int(home_score.strip()),
                                                    'away_score': int(away_score.strip()),
                                                    'full_score': score_text.strip(),
                                                    'league': league or '',  # 添加联赛字段
                                                    'status': 'finished',
                                                    'source': 'sporttery_official',
                                                    'fetched_at': datetime.now().isoformat()
                                                }
                                                results.append(result)
                                                found_codes.add(match_code_cell)
                                                logger.info(f'提取赛果: {match_code_cell} {result["home_team"]} {score_text} {result["away_team"]}')
                                    except Exception as e:
                                        continue
                except Exception as e:
                    logger.warning(f'表格解析失败: {e}')
            
            # 方法2：如果表格解析失败，尝试从页面文本中提取
            if not results:
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    # 使用正则表达式查找已结束比赛的赛果
                    result_pattern = r'(周[一二三四五六日]\d{3})\s*([^\n]+?)\s*(\S+)\s+(\d+:\d+)\s+(\S+)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})'
                    result_matches = re.findall(result_pattern, page_text, re.DOTALL)
                    
                    for match in result_matches:
                        match_code, league, home_team, score, away_team, match_time = match
                        
                        if ':' in score:
                            match_code_stripped = match_code.strip()
                            # 如果指定了目标match_code列表，只保存目标编号的赛果
                            if target_match_codes and match_code_stripped not in target_match_codes:
                                continue
                            
                            home_score, away_score = score.split(':')
                            result = {
                                'match_code': match_code_stripped,
                                'home_team': home_team.strip(),
                                'away_team': away_team.strip(),
                                'home_score': int(home_score.strip()),
                                'away_score': int(away_score.strip()),
                                'full_score': f"{home_score.strip()}:{away_score.strip()}",
                                'league': league.strip() if league else '',  # 添加联赛字段
                                'status': 'finished',
                                'source': 'sporttery_official',
                                'fetched_at': datetime.now().isoformat()
                            }
                            results.append(result)
                            found_codes.add(match_code_stripped)
                            logger.info(f'提取赛果: {match_code_stripped} {home_team} {score} {away_team}')
                except Exception as e:
                    logger.error(f'文本解析也失败: {e}')
            
            logger.info(f'成功提取 {len(results)} 个赛果')
            
            # 如果指定了目标match_code且还有未找到的，尝试翻页继续查找
            if target_match_codes:
                missing_codes = set(target_match_codes) - found_codes
                if missing_codes:
                    logger.info(f'当前页找到 {len(found_codes)}/{len(target_match_codes)} 个目标赛果，还有 {len(missing_codes)} 个未找到，尝试翻页查找')
                    # 尝试翻页查找（最多翻5页）
                    page_results = await self._try_pagination_for_results(target_match_codes, missing_codes, found_codes)
                    results.extend(page_results)
                    logger.info(f'翻页后总共找到 {len(results)} 个赛果')
        
        except Exception as e:
            logger.error(f'提取赛果失败: {str(e)}')
        
        return results
    
    async def _try_pagination_for_results(self, target_match_codes: List[str], missing_codes: set, found_codes: set, max_pages: int = 5):
        """尝试翻页查找缺失的赛果"""
        page_results = []
        page_count = 0
        
        try:
            while page_count < max_pages and missing_codes:
                # 尝试查找"下一页"按钮
                try:
                    next_button = None
                    # 常见的"下一页"按钮选择器
                    next_selectors = [
                        "a:contains('下一页')",
                        "a:contains('下页')",
                        "button:contains('下一页')",
                        ".next-page",
                        "#next-page",
                        "a[title*='下一页']",
                        "a[title*='下页']"
                    ]
                    
                    # 也尝试通过XPath查找
                    try:
                        next_button = self.driver.find_element(By.XPATH, "//a[contains(text(), '下一页')] | //a[contains(text(), '下页')] | //button[contains(text(), '下一页')]")
                    except:
                        pass
                    
                    if not next_button:
                        # 尝试CSS选择器
                        for selector in next_selectors:
                            try:
                                next_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                                break
                            except:
                                continue
                    
                    if not next_button or not next_button.is_displayed():
                        logger.info("未找到下一页按钮，可能已到最后一页")
                        break
                    
                    # 点击下一页
                    next_button.click()
                    logger.info(f'已点击下一页按钮（第 {page_count + 1} 页）')
                    await asyncio.sleep(3)  # 等待页面加载
                    
                    # 提取当前页的赛果
                    page_data = await self._extract_results_from_current_page(target_match_codes, found_codes)
                    page_results.extend(page_data)
                    
                    # 更新已找到的编号
                    for result in page_data:
                        found_codes.add(result.get('match_code'))
                    
                    # 更新缺失列表
                    missing_codes = set(target_match_codes) - found_codes
                    
                    if not missing_codes:
                        logger.info('所有目标赛果都已找到，停止翻页')
                        break
                    
                    page_count += 1
                    
                except Exception as e:
                    logger.warning(f'翻页失败: {e}')
                    break
                    
        except Exception as e:
            logger.error(f'翻页查找过程出错: {e}')
        
        return page_results
    
    async def _extract_results_from_current_page(self, target_match_codes: List[str], found_codes: set) -> List[Dict]:
        """从当前页面提取赛果（简化版，只提取当前页）"""
        results = []
        
        try:
            # 查找所有包含比分的元素
            score_spans = self.driver.find_elements(By.CSS_SELECTOR, 'span.u-org')
            score_tds = self.driver.find_elements(By.XPATH, '//td[@width="60"]')
            all_score_elements = list(score_spans) + list(score_tds)
            
            for score_elem in all_score_elements:
                try:
                    score_text = score_elem.text.strip()
                    if ':' in score_text and score_text.count(':') == 1:
                        parts = score_text.split(':')
                        if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                            try:
                                row = score_elem.find_element(By.XPATH, './ancestor::tr')
                                if row:
                                    cells = row.find_elements(By.TAG_NAME, "td")
                                    
                                    # 提取比赛编号
                                    match_code = None
                                    for cell in cells:
                                        cell_text = cell.text.strip()
                                        if '周' in cell_text and any(c.isdigit() for c in cell_text):
                                            match_obj = re.search(r'周[一二三四五六日]\d{3}', cell_text)
                                            if match_obj:
                                                match_code = match_obj.group(0)
                                                break
                                    
                                    if match_code:
                                        # 只保存目标编号且未找到的赛果
                                        if target_match_codes and match_code not in target_match_codes:
                                            continue
                                        if match_code in found_codes:
                                            continue  # 已找到，跳过
                                        
                                        # 提取联赛和队伍信息（简化版）
                                        league = None
                                        home_team = ''
                                        away_team = ''
                                        
                                        try:
                                            league_divs = row.find_elements(By.CSS_SELECTOR, 'div.league-bg')
                                            if league_divs:
                                                league = league_divs[0].text.strip()
                                        except:
                                            pass
                                        
                                        for cell in cells:
                                            cell_text = cell.text.strip()
                                            if 'VS' in cell_text.upper() or 'vs' in cell_text:
                                                parts_teams = re.split(r'\s*(?:VS|vs)\s*', cell_text, 1)
                                                if len(parts_teams) >= 2:
                                                    home_team = re.sub(r'\([^)]*\)', '', parts_teams[0]).strip()
                                                    away_team = re.sub(r'\([^)]*\)', '', parts_teams[1]).strip()
                                                    break
                                        
                                        result = {
                                            'match_code': match_code,
                                            'home_team': home_team or '',
                                            'away_team': away_team or '',
                                            'home_score': int(parts[0]),
                                            'away_score': int(parts[1]),
                                            'full_score': score_text,
                                            'league': league or '',
                                            'status': 'finished',
                                            'source': 'sporttery_official',
                                            'fetched_at': datetime.now().isoformat()
                                        }
                                        results.append(result)
                                        logger.debug(f'翻页提取赛果: {match_code} {score_text}')
                            except:
                                continue
                except:
                    continue
                    
        except Exception as e:
            logger.warning(f'从当前页提取赛果失败: {e}')
        
        return results
    
    def collect_all_matches(self):
        """收集所有比赛数据（定时任务调用）"""
        try:
            logger.info("开始收集所有比赛数据")
            self._setup_driver()
            self.driver.get(self.base_url)
            
            # 等待页面加载
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "match-item"))
            )
            
            matches = self._extract_matches()
            logger.info(f"成功收集到 {len(matches)} 场比赛数据")
            return matches
            
        except Exception as e:
            logger.error(f"收集比赛数据失败: {e}")
            return []
        finally:
            self.close()
    
    async def _extract_match_results(self):
        """提取比赛结果（定时任务调用）- 异步版本，支持日期筛选"""
        try:
            logger.info("开始提取比赛结果")
            self._setup_driver()
            
            # 访问赛果页面（不是赛程页面）
            results_url = 'https://www.sporttery.cn/jc/zqsgkj/'
            self.driver.get(results_url)
            logger.info(f'正在访问赛果页面: {results_url}')
            
            # 等待页面加载
            await asyncio.sleep(3)
            try:
                # 尝试等待日期筛选控件加载
                self.wait.until(
                    EC.presence_of_element_located((By.ID, "start_date"))
                )
            except:
                logger.warning("未找到日期筛选控件，继续使用默认页面")
                await asyncio.sleep(5)
            
            # 尝试设置日期筛选（从数据库查询过去两天的下注时间）
            date_range = self._get_date_range_from_database()
            if date_range:
                start_date, end_date = date_range
                logger.info(f'设置日期筛选范围: {start_date} 到 {end_date}')
                
                try:
                    # 设置开始日期
                    start_date_input = self.driver.find_element(By.ID, "start_date")
                    # 清空并设置日期
                    start_date_input.clear()
                    start_date_input.send_keys(start_date)
                    logger.info(f'已设置开始日期: {start_date}')
                    
                    await asyncio.sleep(1)
                    
                    # 设置结束日期
                    end_date_input = self.driver.find_element(By.ID, "end_date")
                    end_date_input.clear()
                    end_date_input.send_keys(end_date)
                    logger.info(f'已设置结束日期: {end_date}')
                    
                    await asyncio.sleep(1)
                    
                    # 尝试触发查询（可能需要点击查询按钮或触发日期选择器的change事件）
                    # 方法1：触发日期输入框的change事件
                    self.driver.execute_script("""
                        var startDate = arguments[0];
                        var endDate = arguments[1];
                        var startInput = document.getElementById('start_date');
                        var endInput = document.getElementById('end_date');
                        if (startInput) {
                            startInput.value = startDate;
                            startInput.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                        if (endInput) {
                            endInput.value = endDate;
                            endInput.dispatchEvent(new Event('change', { bubbles: true }));
                        }
                    """, start_date, end_date)
                    
                    # 方法2：查找并点击查询按钮（如果有）
                    try:
                        query_clicked = False
                        
                        # 查找可能的查询按钮（常见的选择器）
                        query_selectors = [
                            "input[type='submit']",
                            "button[type='submit']",
                            ".query-btn",
                            "#query-btn",
                            "button.btn",
                            "input.btn"
                        ]
                        
                        # 也尝试通过文本查找
                        try:
                            # 查找包含"查询"文字的按钮
                            query_btn = self.driver.find_element(By.XPATH, "//input[@value='查询'] | //button[contains(text(), '查询')]")
                            if query_btn.is_displayed():
                                query_btn.click()
                                logger.info('已点击查询按钮（通过文本查找）')
                                query_clicked = True
                        except:
                            pass
                        
                        if not query_clicked:
                            for selector in query_selectors:
                                try:
                                    query_btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                                    if query_btn.is_displayed():
                                        query_btn.click()
                                        logger.info(f'已点击查询按钮: {selector}')
                                        query_clicked = True
                                        break
                                except:
                                    continue
                        
                        if not query_clicked:
                            logger.info("未找到查询按钮，等待页面自动刷新")
                        
                    except Exception as e:
                        logger.debug(f"查找查询按钮失败: {e}")
                    
                    # 等待页面刷新/加载
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    logger.warning(f"设置日期筛选失败: {e}，继续使用默认页面")
            else:
                logger.info("未找到数据库中的日期范围，使用默认页面")
            
            # 等待页面内容加载
            await asyncio.sleep(3)
            try:
                # 尝试等待赛果页面的常见元素
                self.wait.until(
                    EC.presence_of_element_located((By.TAG_NAME, "table"))
                )
            except:
                logger.warning("未找到table元素，继续尝试提取")
            
            await asyncio.sleep(2)
            
            # 从数据库获取目标match_code列表（基于赛程）
            target_match_codes = self._get_target_match_codes_from_database()
            if target_match_codes:
                logger.info(f'从数据库获取到 {len(target_match_codes)} 个目标比赛编号，将只抓取这些比赛的赛果')
            else:
                logger.warning("未找到目标比赛编号，将抓取所有赛果")
            
            # 正确调用异步方法，传入目标match_code列表
            results = await self._extract_results(target_match_codes=target_match_codes)
            logger.info(f"成功提取到 {len(results)} 个比赛结果")
            
            # 检查是否所有目标match_code都已找到
            if target_match_codes:
                found_codes = set(r.get('match_code') for r in results)
                missing_codes = set(target_match_codes) - found_codes
                if missing_codes:
                    logger.warning(f'有 {len(missing_codes)} 个比赛编号未找到赛果: {sorted(list(missing_codes))[:10]}...')
                else:
                    logger.info('所有目标比赛编号都已找到赛果')
            
            return results
            
        except Exception as e:
            logger.error(f"提取比赛结果失败: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None
    
    def _get_date_range_from_database(self):
        """从数据库查询过去两天的下注时间，计算日期范围"""
        try:
            import sqlite3
            from datetime import datetime, timedelta
            
            conn = sqlite3.connect("system.db")
            cursor = conn.cursor()
            
            # 查询过去两天的所有不重复的group_date
            two_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT DISTINCT group_date 
                FROM lottery_matches 
                WHERE group_date >= ? 
                AND group_date IS NOT NULL 
                AND group_date != ''
                ORDER BY group_date ASC
            ''', (two_days_ago,))
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                logger.warning("数据库中未找到过去两天的下注时间")
                return None
            
            # 提取所有日期
            dates = [row[0] for row in rows if row[0]]
            if not dates:
                return None
            
            # 转换为日期对象并排序
            date_objects = []
            for date_str in dates:
                try:
                    date_obj = datetime.strptime(date_str[:10], '%Y-%m-%d')
                    date_objects.append(date_obj)
                except:
                    continue
            
            if not date_objects:
                return None
            
            # 找到最早和最晚的日期
            min_date = min(date_objects)
            max_date = max(date_objects)
            
            # 计算日期范围：最早-1天 到 最晚+1天
            start_date = (min_date - timedelta(days=1)).strftime('%Y-%m-%d')
            end_date = (max_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            logger.info(f'从数据库查询到的日期范围: 最早={min_date.strftime("%Y-%m-%d")}, 最晚={max_date.strftime("%Y-%m-%d")}')
            logger.info(f'计算后的查询范围: {start_date} 到 {end_date}')
            
            return (start_date, end_date)
            
        except Exception as e:
            logger.error(f"从数据库查询日期范围失败: {e}")
            return None
    
    def _get_target_match_codes_from_database(self):
        """从数据库查询最近两天的所有match_code（用于赛果抓取）"""
        try:
            import sqlite3
            from datetime import datetime, timedelta
            
            conn = sqlite3.connect("system.db")
            cursor = conn.cursor()
            
            # 查询过去两天的所有match_code
            two_days_ago = (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT DISTINCT match_code 
                FROM lottery_matches 
                WHERE group_date >= ? 
                AND match_code IS NOT NULL 
                AND match_code != ''
                AND is_active = 1
                ORDER BY match_code ASC
            ''', (two_days_ago,))
            
            rows = cursor.fetchall()
            conn.close()
            
            if not rows:
                logger.warning("数据库中未找到过去两天的比赛编号")
                return None
            
            # 提取所有match_code
            match_codes = [row[0] for row in rows if row[0]]
            
            if not match_codes:
                return None
            
            logger.info(f'从数据库查询到 {len(match_codes)} 个目标比赛编号')
            return match_codes
            
        except Exception as e:
            logger.error(f"从数据库查询比赛编号失败: {e}")
            return None
    
    def close(self):
        """关闭浏览器驱动"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
                logger.info("浏览器驱动已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器驱动失败: {e}")


# 创建抓取器实例
lottery_scraper = LotteryScraper()

