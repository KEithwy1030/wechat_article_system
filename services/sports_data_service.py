"""
体育数据爬取服务
专门爬取体育网站的比赛数据，简单实用，维护成本低
"""

import logging
import requests
import time
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class SportsDataService:
    """体育数据爬取服务"""
    
    def __init__(self):
        # 请求头配置
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # 请求会话
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # 目标网站配置
        self.sports_sites = {
            'espn': {
                'base_url': 'https://www.espn.com',
                'search_path': '/soccer/scoreboard',
                'match_path': '/soccer/match'
            },
            'bbc': {
                'base_url': 'https://www.bbc.com/sport',
                'search_path': '/football',
                'match_path': '/football'
            }
        }
        
        logger.info("体育数据爬取服务初始化完成")
    
    def get_match_data(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """
        获取比赛数据
        
        Args:
            home_team: 主队名称
            away_team: 客队名称
            
        Returns:
            比赛数据字典
        """
        try:
            logger.info(f"开始爬取比赛数据: {home_team} vs {away_team}")
            
            # 第一步：搜索比赛
            match_url = self._find_match_url(home_team, away_team)
            if not match_url:
                logger.warning("未找到比赛链接")
                return self._get_fallback_data(home_team, away_team)
            
            # 第二步：爬取比赛详情
            match_data = self._scrape_match_details(match_url)
            
            # 第三步：爬取球队信息
            home_team_data = self._scrape_team_data(home_team)
            away_team_data = self._scrape_team_data(away_team)
            
            # 第四步：聚合数据
            aggregated_data = self._aggregate_match_data(
                match_data, home_team_data, away_team_data, home_team, away_team
            )
            
            logger.info(f"比赛数据爬取完成: {home_team} vs {away_team}")
            return aggregated_data
            
        except Exception as e:
            logger.error(f"爬取比赛数据失败: {e}")
            return self._get_fallback_data(home_team, away_team)
    
    def _find_match_url(self, home_team: str, away_team: str) -> Optional[str]:
        """查找比赛链接"""
        try:
            # 构建搜索查询
            search_query = f"{home_team} vs {away_team}"
            
            # 尝试ESPN搜索
            espn_url = self._search_espn(search_query)
            if espn_url:
                return espn_url
            
            # 尝试BBC搜索
            bbc_url = self._search_bbc(search_query)
            if bbc_url:
                return bbc_url
            
            return None
            
        except Exception as e:
            logger.error(f"搜索比赛链接失败: {e}")
            return None
    
    def _search_espn(self, query: str) -> Optional[str]:
        """在ESPN搜索比赛"""
        try:
            # 使用ESPN的搜索功能
            search_url = f"https://www.espn.com/soccer/search?q={query}"
            
            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找比赛链接
            match_links = soup.find_all('a', href=re.compile(r'/soccer/match/'))
            
            for link in match_links:
                href = link.get('href')
                if href:
                    return urljoin('https://www.espn.com', href)
            
            return None
            
        except Exception as e:
            logger.error(f"ESPN搜索失败: {e}")
            return None
    
    def _search_bbc(self, query: str) -> Optional[str]:
        """在BBC搜索比赛"""
        try:
            # 使用BBC的搜索功能
            search_url = f"https://www.bbc.com/sport/search?q={query}"
            
            response = self.session.get(search_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 查找比赛链接
            match_links = soup.find_all('a', href=re.compile(r'/sport/football/'))
            
            for link in match_links:
                href = link.get('href')
                if href and 'match' in href.lower():
                    return urljoin('https://www.bbc.com', href)
            
            return None
            
        except Exception as e:
            logger.error(f"BBC搜索失败: {e}")
            return None
    
    def _scrape_match_details(self, match_url: str) -> Dict[str, Any]:
        """爬取比赛详情"""
        try:
            response = self.session.get(match_url, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 提取比赛基本信息
            match_data = {
                'url': match_url,
                'title': self._extract_title(soup),
                'date': self._extract_match_date(soup),
                'venue': self._extract_venue(soup),
                'competition': self._extract_competition(soup),
                'head_to_head': self._extract_head_to_head(soup),
                'form': self._extract_team_form(soup),
                'news': self._extract_match_news(soup)
            }
            
            return match_data
            
        except Exception as e:
            logger.error(f"爬取比赛详情失败: {e}")
            return {}
    
    def _scrape_team_data(self, team_name: str) -> Dict[str, Any]:
        """爬取球队数据"""
        try:
            # 搜索球队页面
            search_url = f"https://www.espn.com/soccer/team/_/name/{team_name.lower().replace(' ', '-')}"
            
            response = self.session.get(search_url, timeout=15)
            if response.status_code == 404:
                # 如果404，尝试其他搜索方式
                return self._get_basic_team_data(team_name)
            
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            team_data = {
                'name': team_name,
                'form': self._extract_team_form_from_page(soup),
                'stats': self._extract_team_stats(soup),
                'squad': self._extract_squad_info(soup),
                'news': self._extract_team_news(soup)
            }
            
            return team_data
            
        except Exception as e:
            logger.error(f"爬取球队数据失败: {e}")
            return self._get_basic_team_data(team_name)
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """提取页面标题"""
        try:
            title = soup.find('title')
            return title.get_text().strip() if title else ""
        except:
            return ""
    
    def _extract_match_date(self, soup: BeautifulSoup) -> str:
        """提取比赛日期"""
        try:
            # 查找日期元素
            date_elem = soup.find(['time', 'span'], class_=re.compile(r'date|time'))
            if date_elem:
                return date_elem.get_text().strip()
            return ""
        except:
            return ""
    
    def _extract_venue(self, soup: BeautifulSoup) -> str:
        """提取比赛场地"""
        try:
            venue_elem = soup.find(['span', 'div'], class_=re.compile(r'venue|stadium'))
            if venue_elem:
                return venue_elem.get_text().strip()
            return ""
        except:
            return ""
    
    def _extract_competition(self, soup: BeautifulSoup) -> str:
        """提取赛事名称"""
        try:
            comp_elem = soup.find(['span', 'div'], class_=re.compile(r'competition|league'))
            if comp_elem:
                return comp_elem.get_text().strip()
            return ""
        except:
            return ""
    
    def _extract_head_to_head(self, soup: BeautifulSoup) -> str:
        """提取历史交锋记录"""
        try:
            h2h_elem = soup.find(['div', 'section'], class_=re.compile(r'head-to-head|h2h'))
            if h2h_elem:
                return h2h_elem.get_text().strip()
            return ""
        except:
            return ""
    
    def _extract_team_form(self, soup: BeautifulSoup) -> Dict[str, str]:
        """提取两队状态"""
        try:
            form_data = {}
            form_elements = soup.find_all(['div', 'span'], class_=re.compile(r'form|recent'))
            
            for elem in form_elements:
                text = elem.get_text().strip()
                if len(text) > 10:  # 过滤太短的内容
                    form_data['form'] = text
                    break
            
            return form_data
        except:
            return {}
    
    def _extract_match_news(self, soup: BeautifulSoup) -> str:
        """提取比赛新闻"""
        try:
            news_elem = soup.find(['div', 'article'], class_=re.compile(r'news|story|article'))
            if news_elem:
                return news_elem.get_text().strip()
            return ""
        except:
            return ""
    
    def _extract_team_form_from_page(self, soup: BeautifulSoup) -> str:
        """从球队页面提取状态"""
        try:
            form_elem = soup.find(['div', 'span'], class_=re.compile(r'form|recent'))
            if form_elem:
                return form_elem.get_text().strip()
            return ""
        except:
            return ""
    
    def _extract_team_stats(self, soup: BeautifulSoup) -> Dict[str, str]:
        """提取球队统计数据"""
        try:
            stats = {}
            stat_elements = soup.find_all(['div', 'span'], class_=re.compile(r'stat|data'))
            
            for elem in stat_elements:
                text = elem.get_text().strip()
                if ':' in text and len(text) < 100:  # 过滤格式化的数据
                    stats['stats'] = text
                    break
            
            return stats
        except:
            return {}
    
    def _extract_squad_info(self, soup: BeautifulSoup) -> str:
        """提取阵容信息"""
        try:
            squad_elem = soup.find(['div', 'section'], class_=re.compile(r'squad|players'))
            if squad_elem:
                return squad_elem.get_text().strip()
            return ""
        except:
            return ""
    
    def _extract_team_news(self, soup: BeautifulSoup) -> str:
        """提取球队新闻"""
        try:
            news_elem = soup.find(['div', 'article'], class_=re.compile(r'news|story'))
            if news_elem:
                return news_elem.get_text().strip()
            return ""
        except:
            return ""
    
    def _get_basic_team_data(self, team_name: str) -> Dict[str, Any]:
        """获取基础球队数据"""
        return {
            'name': team_name,
            'form': '近期状态数据待更新',
            'stats': {'stats': '统计数据待更新'},
            'squad': '阵容信息待更新',
            'news': '球队新闻待更新'
        }
    
    def _aggregate_match_data(self, match_data: Dict, home_data: Dict, 
                            away_data: Dict, home_team: str, away_team: str) -> Dict[str, Any]:
        """聚合比赛数据"""
        try:
            # 构建聚合内容
            content_parts = []
            
            # 比赛基本信息
            if match_data.get('title'):
                content_parts.append(f"比赛: {match_data['title']}")
            if match_data.get('date'):
                content_parts.append(f"时间: {match_data['date']}")
            if match_data.get('venue'):
                content_parts.append(f"场地: {match_data['venue']}")
            if match_data.get('competition'):
                content_parts.append(f"赛事: {match_data['competition']}")
            
            # 历史交锋
            if match_data.get('head_to_head'):
                content_parts.append(f"历史交锋: {match_data['head_to_head']}")
            
            # 球队状态
            if home_data.get('form'):
                content_parts.append(f"{home_team}状态: {home_data['form']}")
            if away_data.get('form'):
                content_parts.append(f"{away_team}状态: {away_data['form']}")
            
            # 球队数据
            if home_data.get('stats'):
                content_parts.append(f"{home_team}数据: {home_data['stats']}")
            if away_data.get('stats'):
                content_parts.append(f"{away_team}数据: {away_data['stats']}")
            
            # 新闻信息
            if match_data.get('news'):
                content_parts.append(f"比赛新闻: {match_data['news']}")
            
            aggregated_content = '\n\n'.join(content_parts)
            
            return {
                'success': True,
                'match_title': f"{home_team} vs {away_team}",
                'aggregated_content': aggregated_content,
                'match_data': match_data,
                'home_team_data': home_data,
                'away_team_data': away_data,
                'sources': [
                    {'name': 'ESPN', 'url': match_data.get('url', '')},
                    {'name': 'BBC Sport', 'url': ''}
                ],
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"聚合数据失败: {e}")
            return self._get_fallback_data(home_team, away_team)
    
    def _extract_team_names(self, title: str) -> List[str]:
        """从标题中提取球队名称"""
        # 匹配常见的比赛标题格式
        patterns = [
            r'([^vs]+)\s+vs\s+([^，。！？\-]+)',
            r'([^对]+)\s+对\s+([^，。！？\-]+)',
            r'([^战]+)\s+战\s+([^，。！？\-]+)',
            r'([^：]+)\s*：\s*([^，。！？\-]+)',
            r'([^-]+)\s*-\s*([^，。！？]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                team1 = match.group(1).strip()
                team2 = match.group(2).strip()
                
                # 清理球队名称
                team1 = re.sub(r'[^\w\u4e00-\u9fff]', '', team1)
                team2 = re.sub(r'[^\w\u4e00-\u9fff]', '', team2)
                
                if len(team1) > 1 and len(team2) > 1:
                    return [team1, team2]
        
        return []
    
    def _get_fallback_data(self, home_team: str, away_team: str) -> Dict[str, Any]:
        """获取备用数据"""
        fallback_content = f"""
比赛: {home_team} vs {away_team}
时间: 待确认
场地: 待确认

{home_team}状态: 近期状态良好，球员状态稳定
{away_team}状态: 近期状态良好，球员状态稳定

历史交锋: 两队历史交锋记录丰富，互有胜负
比赛预测: 基于双方近期状态和历史交锋，预计将是一场激烈的比赛

注意: 此数据为备用数据，建议手动核实最新信息。
        """
        
        return {
            'success': True,
            'match_title': f"{home_team} vs {away_team}",
            'aggregated_content': fallback_content.strip(),
            'match_data': {},
            'home_team_data': {},
            'away_team_data': {},
            'sources': [],
            'timestamp': datetime.now().isoformat(),
            'is_fallback': True
        }
