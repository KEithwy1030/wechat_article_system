import requests
import json
import base64
import os
from app_config import setup_logging

logger = setup_logging()

class ZhipuService:
    def __init__(self):
        self.api_key = None
        self.model = "glm-4.5-air"
        self.base_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        # 自动加载配置
        self._load_config_from_file()
    
    def _load_config_from_file(self):
        """从配置文件自动加载智谱AI配置"""
        try:
            from services.config_service import ConfigService
            config_service = ConfigService()
            zhipu_config = config_service.get_zhipu_config()
            
            if zhipu_config.get('api_key'):
                self.api_key = zhipu_config['api_key']
                self.model = zhipu_config.get('model', 'glm-4.5-air')
                logger.info(f"智谱AI配置已自动加载: 模型={self.model}")
            else:
                logger.info("配置文件中未找到智谱AI API密钥，使用默认配置")
        except Exception as e:
            logger.warning(f"自动加载智谱AI配置失败: {e}")
        
    def set_config(self, api_key, model="glm-4.5-air"):
        """设置智谱AI配置"""
        self.api_key = api_key
        self.model = model
        logger.info(f"智谱AI配置已更新: 模型={model}")
    
    def reload_config(self):
        """从统一配置服务重新加载配置"""
        try:
            from services.config_service import ConfigService
            config_service = ConfigService()
            zhipu_config = config_service.get_zhipu_config()
            
            self.api_key = zhipu_config.get('api_key')
            self.model = zhipu_config.get('model', 'glm-4.5-air')
            
            if self.api_key:
                logger.info(f"智谱AI配置已重新加载: 模型={self.model}")
            else:
                logger.info("智谱AI配置已重新加载: API密钥为空")
                
        except Exception as e:
            logger.warning(f"重新加载智谱AI配置失败: {e}")
        
    def test_connection(self):
        """测试智谱AI连接"""
        if not self.api_key:
            return {"success": False, "message": "API密钥未配置"}
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "user", "content": "你好，请回复'连接成功'"}
                ],
                "max_tokens": 50
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"success": True, "message": "连接成功", "response": content}
            else:
                error_msg = f"API调用失败: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_message = error_detail.get('error', {}).get('message', '')
                    error_code = error_detail.get('error', {}).get('code', '')
                    error_msg += f" - {error_message}"
                    
                    # 特别处理模型不存在的错误
                    if '模型' in error_message or 'model' in error_message.lower():
                        error_msg += f"\n提示：智谱AI多模态模型名称应为 'glm-4.5v'（支持图片识别功能）"
                except:
                    error_msg += f" - {response.text}"
                return {"success": False, "message": error_msg}
                
        except requests.exceptions.Timeout:
            return {"success": False, "message": "连接超时，请检查网络"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"网络请求失败: {str(e)}"}
        except Exception as e:
            logger.error(f"智谱AI连接测试失败: {str(e)}")
            return {"success": False, "message": f"连接测试失败: {str(e)}"}
    
    def chat_completion(self, messages, max_tokens=1000, temperature=0.7):
        """调用智谱AI进行对话"""
        if not self.api_key:
            return {"success": False, "message": "API密钥未配置"}
            
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"success": True, "content": content, "usage": result.get("usage", {})}
            else:
                error_msg = f"API调用失败: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail.get('error', {}).get('message', '')}"
                except:
                    error_msg += f" - {response.text}"
                return {"success": False, "message": error_msg}
                
        except requests.exceptions.Timeout:
            return {"success": False, "message": "请求超时"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"网络请求失败: {str(e)}"}
        except Exception as e:
            logger.error(f"智谱AI对话失败: {str(e)}")
            return {"success": False, "message": f"对话失败: {str(e)}"}
    
    def parse_user_command(self, user_input):
        """解析用户指令，返回系统操作类型和参数"""
        system_prompt = """你是一个智能助手，专门帮助用户操作系统功能。请分析用户的指令，并返回JSON格式的响应。

系统功能包括：
1. 数据搜集状态检查 - 关键词：检查、状态、数据搜集、搜集状态
2. 生成文章 - 关键词：生成、写、创建文章、新文章
3. 审核文章 - 关键词：审核、审查、待审核、文章审核
4. 触发数据搜集 - 关键词：触发、开始、搜集、数据搜集
5. 查看历史 - 关键词：历史、记录、生成历史、发布历史
6. 系统状态 - 关键词：系统状态、运行情况、系统情况
7. 查询比赛 - 关键词：查询比赛、哪些比赛、需要撰写、比赛列表、即将进行的比赛

请返回JSON格式：
{
    "action": "操作类型",
    "params": {},
    "message": "回复给用户的友好消息"
}

操作类型包括：check_status, generate_article, review_articles, trigger_collection, view_history, system_status, query_matches, general_chat"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ]
        
        result = self.chat_completion(messages, max_tokens=200)
        if result["success"]:
            try:
                # 尝试解析JSON响应
                response_text = result["content"].strip()
                if response_text.startswith("```json"):
                    response_text = response_text.replace("```json", "").replace("```", "").strip()
                elif response_text.startswith("```"):
                    response_text = response_text.replace("```", "").strip()
                
                parsed_response = json.loads(response_text)
                return {"success": True, "parsed": parsed_response}
            except json.JSONDecodeError:
                # 如果不是JSON格式，作为一般对话处理
                return {
                    "success": True, 
                    "parsed": {
                        "action": "general_chat",
                        "params": {},
                        "message": result["content"]
                    }
                }
        else:
            return {"success": False, "message": result["message"]}
    
    def analyze_image(self, image_path: str, prompt: str = "请分析这张图片中的内容，提取关键信息") -> dict:
        """
        使用GLM-4V分析图片内容（多模态功能）
        :param image_path: 图片文件路径
        :param prompt: 分析提示词
        :return: 分析结果
        """
        if not self.api_key:
            return {"success": False, "message": "API密钥未配置"}
        
        # 支持的多模态模型列表（根据智谱AI官方文档）
        multimodal_models = ["glm-4.5v"]
        if self.model not in multimodal_models:
            return {"success": False, "message": f"当前模型 {self.model} 不支持多模态功能，请切换到 {', '.join(multimodal_models)} 之一"}
        
        try:
            # 检查图片文件是否存在
            if not os.path.exists(image_path):
                return {"success": False, "message": f"图片文件不存在: {image_path}"}
            
            # 读取并编码图片
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # 获取图片文件扩展名
            file_extension = os.path.splitext(image_path)[1].lower()
            if file_extension == '.jpg' or file_extension == '.jpeg':
                media_type = "image/jpeg"
            elif file_extension == '.png':
                media_type = "image/png"
            elif file_extension == '.gif':
                media_type = "image/gif"
            elif file_extension == '.webp':
                media_type = "image/webp"
            else:
                return {"success": False, "message": f"不支持的图片格式: {file_extension}"}
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建多模态消息
            data = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{image_data}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000,
                "temperature": 0.3
            }
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {
                    "success": True, 
                    "content": content,
                    "usage": result.get("usage", {})
                }
            else:
                error_msg = f"API调用失败: {response.status_code}"
                try:
                    error_detail = response.json()
                    error_msg += f" - {error_detail.get('error', {}).get('message', '')}"
                except:
                    error_msg += f" - {response.text}"
                return {"success": False, "message": error_msg}
                
        except requests.exceptions.Timeout:
            return {"success": False, "message": "请求超时"}
        except requests.exceptions.RequestException as e:
            return {"success": False, "message": f"网络请求失败: {str(e)}"}
        except Exception as e:
            logger.error(f"智谱AI图片分析失败: {str(e)}")
            return {"success": False, "message": f"图片分析失败: {str(e)}"}
    
    def analyze_lottery_screenshot(self, image_path: str) -> dict:
        """
        专门用于分析竞彩数据截图的函数
        :param image_path: 竞彩截图路径
        :return: 结构化的竞彩数据分析结果
        """
        prompt = """请仔细分析这张竞彩数据的截图，提取以下关键信息：

1. 比赛基本信息：
   - 比赛时间
   - 主队vs客队
   - 联赛名称
   - 比赛编号

2. 赔率数据：
   - 胜平负赔率（主胜、平局、客胜）
   - 让球赔率（如有）
   - 大小球赔率（如有）

3. 其他重要信息：
   - 投注热度
   - 特殊标识
   - 推荐信息

请以JSON格式返回结果，确保数据准确完整。"""
        
        result = self.analyze_image(image_path, prompt)
        if result["success"]:
            # 尝试解析JSON格式的回复
            try:
                content = result["content"]
                if content.strip().startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                elif content.strip().startswith("```"):
                    content = content.replace("```", "").strip()
                
                parsed_data = json.loads(content)
                result["parsed_data"] = parsed_data
                return result
            except json.JSONDecodeError:
                # 如果不是JSON格式，返回原始文本
                logger.warning("智谱AI返回的不是标准JSON格式，返回原始文本")
                return result
        else:
            return result

# 创建全局实例
zhipu_service = ZhipuService()
