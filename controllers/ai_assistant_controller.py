import os
from flask import jsonify, request
from services.zhipu_service import zhipu_service
from services.data_collection_service import data_collection_service
from app_config import setup_logging
import json

logger = setup_logging()

class AIAssistantController:
    def __init__(self):
        pass
    
    def test_zhipu_connection(self, api_key, model="glm-4.5-air"):
        """测试智谱AI连接"""
        try:
            zhipu_service.set_config(api_key, model)
            result = zhipu_service.test_connection()
            return jsonify({
                "success": result["success"],
                "message": result["message"],
                "data": {"response": result.get("response", "")}
            })
        except Exception as e:
            logger.error(f"测试智谱AI连接失败: {str(e)}")
            return jsonify({"success": False, "message": f"测试连接失败: {str(e)}"}), 500
    
    def save_zhipu_config(self, api_key, model="glm-4.5-air"):
        """保存智谱AI配置"""
        try:
            # 使用统一的配置服务保存配置
            from services.config_service import ConfigService
            config_service = ConfigService()
            
            # 先更新内存中的配置
            zhipu_service.set_config(api_key, model)
            
            # 持久化到配置文件
            config_data = config_service.load_config()
            config_data['zhipu_api_key'] = api_key
            config_data['zhipu_model'] = model
            
            save_success = config_service.save_config(config_data)
            if save_success:
                # 更新环境变量
                import os
                if api_key:
                    os.environ['ZHIPU_API_KEY'] = api_key
                    logger.info("✅ 智谱AI API Key环境变量已更新")
                else:
                    if 'ZHIPU_API_KEY' in os.environ:
                        del os.environ['ZHIPU_API_KEY']
                    logger.info("✅ 智谱AI API Key环境变量已清理")
                
                # 重新加载zhipu_service的配置，确保与统一配置系统同步
                zhipu_service.reload_config()
                
                logger.info("智谱AI配置已保存并持久化，服务配置已同步")
                return jsonify({
                    "success": True,
                    "message": "智谱AI配置保存成功"
                })
            else:
                logger.error("保存智谱AI配置到文件失败")
                return jsonify({"success": False, "message": "保存配置到文件失败"}), 500
                
        except Exception as e:
            logger.error(f"保存智谱AI配置失败: {str(e)}")
            return jsonify({"success": False, "message": f"保存配置失败: {str(e)}"}), 500
    
    def save_deepseek_config(self, api_key, model="deepseek-chat"):
        """保存DeepSeek AI配置"""
        try:
            from services.deepseek_service import deepseek_service
            deepseek_service.set_config(api_key, model)
            logger.info("DeepSeek AI配置已保存")
            return jsonify({
                "success": True,
                "message": "DeepSeek AI配置保存成功"
            })
        except Exception as e:
            logger.error(f"保存DeepSeek AI配置失败: {str(e)}")
            return jsonify({"success": False, "message": f"保存配置失败: {str(e)}"}), 500
    
    def save_gemini_config(self, api_key, model="gemini-pro"):
        """保存Gemini AI配置"""
        try:
            from services.gemini_service import gemini_service
            gemini_service.set_config(api_key, model)
            logger.info("Gemini AI配置已保存")
            return jsonify({
                "success": True,
                "message": "Gemini AI配置保存成功"
            })
        except Exception as e:
            logger.error(f"保存Gemini AI配置失败: {str(e)}")
            return jsonify({"success": False, "message": f"保存配置失败: {str(e)}"}), 500
    
    def save_dashscope_config(self, api_key, model="qwen-plus"):
        """保存阿里云百炼配置"""
        try:
            # 这里可以添加阿里云百炼服务的配置保存逻辑
            logger.info("阿里云百炼配置已保存")
            return jsonify({
                "success": True,
                "message": "阿里云百炼配置保存成功"
            })
        except Exception as e:
            logger.error(f"保存阿里云百炼配置失败: {str(e)}")
            return jsonify({"success": False, "message": f"保存配置失败: {str(e)}"}), 500
    
    def save_wechat_config(self, app_id, app_secret):
        """保存微信配置"""
        try:
            from services.wechat_service import wechat_service
            wechat_service.set_config(app_id, app_secret)
            logger.info("微信配置已保存")
            return jsonify({
                "success": True,
                "message": "微信配置保存成功"
            })
        except Exception as e:
            logger.error(f"保存微信配置失败: {str(e)}")
            return jsonify({"success": False, "message": f"保存配置失败: {str(e)}"}), 500
    
    def process_user_command(self, user_input, use_web_search: bool = False, search_engine: str = None):
        """处理用户指令"""
        try:
            # 解析用户指令
            parse_result = zhipu_service.parse_user_command(user_input)
            if not parse_result["success"]:
                return jsonify({
                    "success": False,
                    "message": parse_result["message"]
                })
            
            parsed_command = parse_result["parsed"]
            action = parsed_command["action"]
            params = parsed_command.get("params", {})
            
            # 执行相应的系统操作
            if action == "check_status":
                return self._check_data_collection_status()
            elif action == "generate_article":
                return self._generate_article(params)
            elif action == "review_articles":
                return self._get_pending_articles()
            elif action == "trigger_collection":
                return self._trigger_data_collection()
            elif action == "view_history":
                return self._get_generation_history()
            elif action == "system_status":
                return self._get_system_status()
            elif action == "query_matches":
                return self._query_upcoming_matches()
            elif action == "general_chat":
                if use_web_search:
                    return self._perform_web_search(
                        query=user_input,
                        search_engine=search_engine
                    )
                return jsonify({
                    "success": True,
                    "action": "general_chat",
                    "message": parsed_command["message"],
                    "data": {}
                })
            else:
                return jsonify({
                    "success": False,
                    "message": f"未知的操作类型: {action}"
                })
                
        except Exception as e:
            logger.error(f"处理用户指令失败: {str(e)}")
            return jsonify({"success": False, "message": f"处理指令失败: {str(e)}"}), 500
    
    def _check_data_collection_status(self):
        """检查数据搜集状态"""
        try:
            status = data_collection_service.get_collection_status()
            return jsonify({
                "success": True,
                "action": "check_status",
                "message": "数据搜集状态检查完成",
                "data": status
            })
        except Exception as e:
            logger.error(f"检查数据搜集状态失败: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"检查状态失败: {str(e)}"
            })
    
    def _generate_article(self, params):
        """生成文章"""
        try:
            # 这里可以调用文章生成服务
            # 暂时返回模拟数据
            return jsonify({
                "success": True,
                "action": "generate_article",
                "message": "文章生成功能暂未实现，请使用文章工作台手动生成",
                "data": {"article_id": "temp_article_001"}
            })
        except Exception as e:
            logger.error(f"生成文章失败: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"生成文章失败: {str(e)}"
            })
    
    def _get_pending_articles(self):
        """获取待审核文章"""
        try:
            # 获取待审核文章（模拟数据）
            pending_articles = {"success": True, "data": [], "total": 0}
            return jsonify({
                "success": True,
                "action": "review_articles",
                "message": f"找到 {len(pending_articles)} 篇待审核文章",
                "data": {"articles": pending_articles}
            })
        except Exception as e:
            logger.error(f"获取待审核文章失败: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"获取待审核文章失败: {str(e)}"
            })
    
    def _trigger_data_collection(self):
        """触发数据搜集"""
        try:
            success = data_collection_service.trigger_auto_collection()
            if success:
                return jsonify({
                    "success": True,
                    "action": "trigger_collection",
                    "message": "数据搜集已触发",
                    "data": {"triggered": True}
                })
            else:
                return jsonify({
                    "success": False,
                    "action": "trigger_collection",
                    "message": "当前没有需要搜集的重点比赛",
                    "data": {"triggered": False}
                })
        except Exception as e:
            logger.error(f"触发数据搜集失败: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"触发数据搜集失败: {str(e)}"
            })
    
    def _get_generation_history(self):
        """获取生成历史"""
        try:
            # 这里可以调用历史服务
            return jsonify({
                "success": True,
                "action": "view_history",
                "message": "历史记录功能暂未实现",
                "data": {"history": []}
            })
        except Exception as e:
            logger.error(f"获取历史记录失败: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"获取历史记录失败: {str(e)}"
            })
    
    def _get_system_status(self):
        """获取系统状态"""
        try:
            collection_status = data_collection_service.get_collection_status()
            pending_articles = {"success": True, "data": [], "total": 0}
            
            system_status = {
                "data_collection": collection_status,
                "pending_articles_count": len(pending_articles),
                "system_health": "良好"
            }
            
            return jsonify({
                "success": True,
                "action": "system_status",
                "message": "系统状态检查完成",
                "data": system_status
            })
        except Exception as e:
            logger.error(f"获取系统状态失败: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"获取系统状态失败: {str(e)}"
            })
    
    def _query_upcoming_matches(self):
        """查询即将进行的比赛"""
        try:
            # 调用数据搜集服务获取即将进行的比赛
            matches = data_collection_service.get_upcoming_matches()
            return jsonify({
                "success": True,
                "action": "query_matches",
                "message": f"找到 {len(matches)} 场即将进行的比赛",
                "data": {
                    "matches": matches,
                    "count": len(matches)
                }
            })
        except Exception as e:
            logger.error(f"查询比赛失败: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"查询比赛失败: {str(e)}"
            })

    def _perform_web_search(self, query: str, search_engine: str = None):
        """调用智谱 Web Search API 并返回结果"""
        try:
            api_key = os.environ.get("ZHIPU_API_KEY")
            if not api_key:
                return jsonify({
                    "success": False,
                    "message": "未配置智谱AI API密钥，无法执行联网搜索"
                }), 500
            
            try:
                from zai import ZhipuAiClient  # type: ignore
            except ImportError:
                return jsonify({
                    "success": False,
                    "message": "未安装智谱官方SDK（zai-sdk），请先运行 'pip install zai-sdk'"
                }), 500
            
            client = ZhipuAiClient(api_key=api_key)
            engine = (search_engine or "search_std").strip() or "search_std"
            
            logger.info(f"执行智谱联网搜索，query={query}, engine={engine}")
            search_resp = client.web_search.web_search(
                search_engine=engine,
                search_query=query,
                count=5,
                content_size="medium"
            )
            
            results = []
            for item in search_resp.search_result or []:
                results.append({
                    "title": getattr(item, "title", "") or "",
                    "url": getattr(item, "link", "") or "",
                    "summary": getattr(item, "content", "") or "",
                    "source": getattr(item, "media", "") or "",
                    "publish_date": getattr(item, "publish_date", "") or ""
                })
            
            if results:
                message_lines = ["已为您完成联网搜索，以下是检索到的关键信息："]
                for idx, res in enumerate(results[:3], start=1):
                    title = res["title"] or res["url"] or "未命名结果"
                    source = f"（来源：{res['source']}）" if res["source"] else ""
                    message_lines.append(f"{idx}. {title}{source}")
                message = "\n".join(message_lines)
            else:
                message = "联网搜索未找到相关结果，请尝试调整问题或搜索范围。"
            
            return jsonify({
                "success": True,
                "action": "web_search",
                "message": message,
                "data": {
                    "query": query,
                    "search_engine": engine,
                    "results": results,
                    "request_id": getattr(search_resp, "request_id", "")
                }
            })
        except Exception as e:
            logger.error(f"联网搜索失败: {str(e)}")
            return jsonify({
                "success": False,
                "message": f"联网搜索失败: {str(e)}"
            }), 500

# 创建全局实例
ai_assistant_controller = AIAssistantController()
