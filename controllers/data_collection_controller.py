"""
数据搜集控制器 - 处理数据搜集状态和控制的API请求
"""
import json
import logging
from flask import Blueprint, jsonify, request
from services.data_collection_service import data_collection_service

logger = logging.getLogger(__name__)

# 创建蓝图
data_collection_bp = Blueprint('data_collection', __name__)

@data_collection_bp.route('/api/data-collection/status', methods=['GET'])
def get_collection_status():
    """获取数据搜集状态"""
    try:
        status = data_collection_service.get_collection_status()
        return jsonify({
            "success": True,
            "data": status,
            "message": "数据搜集状态获取成功"
        })
    except Exception as e:
        logger.error(f"获取数据搜集状态失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"获取数据搜集状态失败: {str(e)}"
        }), 500

@data_collection_bp.route('/api/data-collection/start', methods=['POST'])
def start_collection():
    """开始数据搜集"""
    try:
        data = request.get_json()
        task_name = data.get('task_name', '手动数据搜集')
        data_sources = data.get('data_sources', ['sporttery_scraper', 'deepseek_web'])
        
        success = data_collection_service.start_collection(task_name, data_sources)
        
        if success:
            return jsonify({
                "success": True,
                "message": "数据搜集已开始"
            })
        else:
            return jsonify({
                "success": False,
                "message": "数据搜集已在运行中"
            }), 400
            
    except Exception as e:
        logger.error(f"开始数据搜集失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"开始数据搜集失败: {str(e)}"
        }), 500

@data_collection_bp.route('/api/data-collection/stop', methods=['POST'])
def stop_collection():
    """停止数据搜集"""
    try:
        data_collection_service.complete_collection(False, 0, "用户手动停止")
        return jsonify({
            "success": True,
            "message": "数据搜集已停止"
        })
    except Exception as e:
        logger.error(f"停止数据搜集失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"停止数据搜集失败: {str(e)}"
        }), 500

@data_collection_bp.route('/api/data-collection/upcoming-matches', methods=['GET'])
def get_upcoming_matches():
    """获取即将进行的比赛"""
    try:
        matches = data_collection_service.get_upcoming_matches()
        return jsonify({
            "success": True,
            "data": matches,
            "message": "即将进行的比赛获取成功"
        })
    except Exception as e:
        logger.error(f"获取即将进行的比赛失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"获取即将进行的比赛失败: {str(e)}"
        }), 500

@data_collection_bp.route('/api/data-collection/trigger-auto', methods=['POST'])
def trigger_auto_collection():
    """触发自动搜集"""
    try:
        success = data_collection_service.trigger_auto_collection()
        
        if success:
            return jsonify({
                "success": True,
                "message": "自动数据搜集已触发"
            })
        else:
            return jsonify({
                "success": False,
                "message": "当前没有需要搜集的重点比赛"
            }), 400
            
    except Exception as e:
        logger.error(f"触发自动搜集失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"触发自动搜集失败: {str(e)}"
        }), 500

@data_collection_bp.route('/api/data-collection/simulate', methods=['POST'])
def simulate_collection():
    """模拟数据搜集过程（用于演示）"""
    try:
        data_collection_service.simulate_collection_process()
        return jsonify({
            "success": True,
            "message": "数据搜集进度已更新"
        })
    except Exception as e:
        logger.error(f"模拟数据搜集失败: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"模拟数据搜集失败: {str(e)}"
        }), 500
