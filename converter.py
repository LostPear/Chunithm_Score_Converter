# ##############################################################################
# #
# #                      CHUNITHM Score Merger Script
# #
# ##############################################################################
# #
# #                           Version: V50KFC Final
# #
# # 本脚本由 Google Gemini 倾情敲出，快感谢Google
# # 
# # (模型基于 Gemini 2.5 Pro)
# #
# # --- 使用说明 ---
# #
# # [所需文件]
# #   - JSON 存档: 一份从 RinNet 导出的 JSON 格式 CHUNITHM 存档。
# #                (需要基于 CHUNITHM VERSE 及更新的版本)
# #   - CSV 档案: 一份从“落雪咖啡屋”导出的 CSV 格式的分数列表。
# #
# # [运行步骤]
# #   1. 将本脚本文件 (.py) 与你的 JSON 和 CSV 文件放置在同一个文件夹中。
# #   2. 修改下方 [配置项] 中的文件名，使其与你的文件名完全一致，并且依据落雪导出的分数列表版本（ 2025 or 2026 ）来选择
# #   3. 打开 CMD (命令提示符) 或其他终端工具。
# #   4. 在终端中进入脚本所在的文件夹。
# #   5. 运行命令: python CHUNITHMScoreMerger.py
# #
# # [注意事项]
# #   - 通过命令行运行本脚本需要您的电脑已安装 Python 环境，请自行安装。
# #   - 推荐你使用Visual Studio Code
# #   - Full Chain 有可能会有小问题,请根据实际情况切换开关
# #   - 由于作者只会叫ai修改和为ai提供建议与及帮ai找他没想到的小问题，所以这个脚本如果出了点小问题或者个体差异的话我直接投降喵
# #
# # [免责声明]
# #   - 作者和RinNet服无关，使用该脚本默认你在已阅读过RinNet的警告“虽然这可以工作，但不建议使用此功能” 
# #   - 使用或滥用此脚本导致的账号问题，本人不承担任何责任
# #   - 本脚本的唯一设计目的是为玩家提供一个方便的、用于迁移个人在其他平台游玩时产生的合法、真实的游戏记录的工具。请不要手动修改 CSV 文件来使用本脚本去伪造、上传虚假分数或用于任何形式的作弊行为。请尊重游戏和其他玩家。
# #   - 本脚本会修改您的存档文件，这是一个具有潜在风险的操作。强烈建议您在使用前，务必手动备份一份原始的 JSON 存档文件！ 对于因使用本脚本（或因脚本中可能存在的未知 Bug）而导致的任何数据丢失、存档损坏或其它不可预见的损失，本人不承担任何责任
# #   - 本脚本仅供个人使用，请不要也不能用于任何商业用途
# #
# ##############################################################################

import json
import csv
import os

# --- 配置项 ---
# 请在这里修改你的文件名
JSON_INPUT_FILE = 'chusan_xxxxxxx_exported.json'
CSV_INPUT_FILE = 'chunithm-scores.csv'

# 版本兼容模式开关
# True  = LMN -> VERSE 模式: 用于合并旧版(2025 LUMINOUS)CSV到新版存档 (默认)
# False = VERSE -> VERSE 模式: 用于合并新版(2026 VERSE)CSV到新版存档
LUMINOUS_CSV_MODE = True

# Full Chain 合并开关
# True = 合并 Full Chain 等级 (默认)
# False = 完全不合并 Full Chain 等级
MERGE_FULL_CHAIN = True

# --- 数据映射区 ---
# 定义了如何将 CSV 中的文本数据转换为游戏存档能识别的数字代码

# 评级 (Rank) -> `scoreRank` 字段
RANK_MAP = {
    'd': 0, 'c': 1, 'b': 2, 'bb': 3, 'bbb': 4, 'a': 5, 'aa': 6, 'aaa': 7,
    's': 8, 'sp': 9, 'ss': 10, 'ssp': 11, 'sss': 12, 'sssp': 13
}
# Full Chain 等级 -> `fullChain` 字段
FULL_CHAIN_MAP = {
    "fullchain": 1, "fullchain1": 1, "fullchain2": 2, "fullchain3": 3, "fullchain4": 4
}

# 为两种兼容模式定义不同的通关标签映射表
# 模式 True: 旧版CSV(LMN) -> 新版存档(VERSE) 的“翻译”映射
LAMP_MAP_LMN_TO_VERSE = {
    'failed': 0, 'clear': 1, 'hard': 2,
    'absolute': 3,    # 旧版 Absolute (150血) -> 新版 Brave (3)
    'absolutep': 4,   # 旧版 Absolute+ (50血) -> 新版 Absolute (4)
    'catastrophy': 6
}
# 模式 False: 新版CSV(VERSE) -> 新版存档(VERSE) 的“直接”映射
LAMP_MAP_VERSE_TO_VERSE = {
    'failed': 0, 'clear': 1, 'hard': 2, 'brave': 3,
    'absolute': 4,    # 新版 Absolute -> 4
    'catastrophy': 6
}


# --- 核心功能函数 ---
def preprocess_csv(csv_path, lamp_map):
    """
    第一步：预处理 CSV 文件，为每首歌的每个难度构建一个“最佳成就档案”。
    这个函数会扫描整个 CSV，确保为每首歌都找到历史最佳的各项成就，
    以解决 CSV 中包含同一歌曲的多个不同时期记录的问题。
    """
    best_scores = {}
    print("\n步骤 1: 正在扫描 CSV 并构建最佳成就档案...")

    try:
        # 使用 'utf-8-sig' 编码可以正确处理带有 BOM 的文件（通常由 Windows 程序生成）
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    music_id = int(row['id'])
                    level_index = int(row['level_index'])
                    record_key = (music_id, level_index)

                    # 提取当前行的所有成就数据
                    current_score = int(row['score'])
                    current_rank = row.get('rank', '').strip()
                    
                    # AJ/FC 识别逻辑
                    # 所有 FC/AJ/AJC 信息都来自于 'full_combo' 列
                    fc_col_str = row.get('full_combo', '').strip().lower()
                    
                    # AJ 的判断：只要 'full_combo' 列中包含 "alljustice" 即可
                    current_aj_bool = 'alljustice' in fc_col_str
                    
                    # FC 的判断：只要 'full_combo' 列有任何内容，就算 FC
                    current_fc_bool = bool(fc_col_str)
                    
                    lamp_text = row.get('clear', '').strip().lower()
                    current_lamp_id = lamp_map.get(lamp_text, 0)
                    
                    # 根据开关决定是否处理 Full Chain
                    current_fc_chain_id = 0
                    if MERGE_FULL_CHAIN:
                        current_fc_chain_id = FULL_CHAIN_MAP.get(row.get('full_chain', '').strip().lower(), 0)

                    # 如果是第一次见到这首歌，直接存入档案
                    if record_key not in best_scores:
                        best_scores[record_key] = {
                            'score': current_score, 'rank': current_rank,
                            'aj_bool': current_aj_bool, 'fc_bool': current_fc_bool,
                            'lamp_id': current_lamp_id, 'fc_chain_id': current_fc_chain_id
                        }
                    else:
                        # 如果已存在，则逐项比较并更新为更好的成就
                        entry = best_scores[record_key]
                        if current_score > entry['score']:
                            entry['score'] = current_score
                            entry['rank'] = current_rank
                        
                        # 更新原则：只要历史上有过一次 AJ/FC，就永远记录为 AJ/FC
                        if current_aj_bool:
                            entry['aj_bool'] = True
                        if current_fc_bool:
                            entry['fc_bool'] = True
                        
                        if current_lamp_id > entry['lamp_id']:
                            entry['lamp_id'] = current_lamp_id
                        if MERGE_FULL_CHAIN and current_fc_chain_id > entry['fc_chain_id']:
                            entry['fc_chain_id'] = current_fc_chain_id
                
                except (ValueError, KeyError, TypeError):
                    # 跳过 CSV 中任何格式不正确的行
                    continue
    except Exception as e:
        print(f"  > 错误: 读取 CSV 文件时发生严重错误: {e}")
        return None
    
    print(f"  > 扫描完成！共构建了 {len(best_scores)} 条独立的最佳成就记录。")
    return best_scores

def main():
    """脚本主执行函数"""
    print("--- CHUNITHM 分数合并脚本 (V50KFC Final) ---")

    # 根据开关选择正确的 LAMP_MAP
    if LUMINOUS_CSV_MODE:
        active_lamp_map = LAMP_MAP_LMN_TO_VERSE
        print("  > 兼容模式: 已启动 (旧版CSV -> 新版存档)")
    else:
        active_lamp_map = LAMP_MAP_VERSE_TO_VERSE
        print("  > 兼容模式: 已关闭 (新版CSV -> 新版存档)")

    # 检查输入文件是否存在
    if not all(os.path.exists(f) for f in [JSON_INPUT_FILE, CSV_INPUT_FILE]):
        print("错误: 输入文件缺失。")
        return

    # 步骤 1: 预处理 CSV，获得最佳成就档案
    best_csv_scores = preprocess_csv(CSV_INPUT_FILE, active_lamp_map)
    if best_csv_scores is None:
        return

    # 步骤 2: 读取 JSON 存档
    print("\n步骤 2: 正在读取 JSON 存档并准备合并...")
    base_name = os.path.splitext(JSON_INPUT_FILE)[0]
    JSON_OUTPUT_FILE = f"{base_name}_merged.json"

    try:
        with open(JSON_INPUT_FILE, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
    except Exception as e:
        print(f"  > 错误: 读取 JSON 文件失败: {e}")
        return

    # 确保 JSON 结构正确
    if 'userMusicDetailList' not in game_data:
        print("  > 错误: 无法在 JSON 存档中找到 'userMusicDetailList'。")
        return
    
    # 为了快速查找，将列表转换为以 (歌曲ID, 难度) 为键的字典
    music_list = game_data['userMusicDetailList']
    music_map = {(item['musicId'], item['level']): item for item in music_list}
    print("  > 读取成功，开始智能合并...")

    updated_records, added_records = 0, 0
    
    # 步骤 3: 使用最佳成就档案进行智能合并
    for record_key, best_data in best_csv_scores.items():
        music_id, level_index = record_key
        
        # 从档案中提取各项最佳成就
        score = best_data['score']
        rank_str = best_data['rank']
        aj_bool = best_data['aj_bool']
        fc_bool = best_data['fc_bool']
        lamp_id = best_data['lamp_id']
        fc_chain_id = best_data['fc_chain_id']

        # 最终逻辑：AJ 必然包含 FC
        if aj_bool:
            fc_bool = True

        # 判断是更新现有记录，还是添加新记录
        if record_key in music_map:
            # --- 更新现有记录 ---
            score_detail = music_map[record_key]
            has_update = False

            # 逐项比较，只有在 CSV 中的成就更好时才更新
            if score > score_detail.get('scoreMax', 0):
                score_detail['scoreMax'] = score
                # [最终修正] 更新 scoreRank 字段
                score_detail['scoreRank'] = RANK_MAP.get(rank_str.lower(), score_detail.get('scoreRank', 0))
                has_update = True
            
            if lamp_id > score_detail.get('isSuccess', 0):
                score_detail['isSuccess'] = lamp_id
                has_update = True
            
            if fc_bool and not score_detail.get('isFullCombo', False):
                score_detail['isFullCombo'] = True
                score_detail['missCount'] = 0
                has_update = True
            
            if aj_bool and not score_detail.get('isAllJustice', False):
                score_detail['isAllJustice'] = True
                score_detail['isFullCombo'] = True # 强制激活 FC
                score_detail['missCount'] = 0
                has_update = True
            
            # 根据开关决定是否更新 Full Chain
            if MERGE_FULL_CHAIN and fc_chain_id > score_detail.get('fullChain', 0):
                score_detail['fullChain'] = fc_chain_id
                has_update = True
            
            # 如果有任何更新，增加游戏次数
            if has_update:
                updated_records += 1
                score_detail['playCount'] = score_detail.get('playCount', 0) + 1
        
        else:
            # --- 添加新记录 ---
            miss_count = 0 if fc_bool else -1
            # 根据开关决定新纪录的 Full Chain 值
            final_fc_chain_id = fc_chain_id if MERGE_FULL_CHAIN else 0
            
            entry = {
                "musicId": music_id, "level": level_index, "playCount": 1,
                "scoreMax": score, 
                "scoreRank": RANK_MAP.get(rank_str.lower(), 0),
                "isFullCombo": fc_bool, "isAllJustice": aj_bool,
                "isSuccess": lamp_id,
                "fullChain": final_fc_chain_id, "ext1": 0,
                "maxComboCount": 0, "maxChain": 0, "isLock": False, "theoryCount": 0
            }
            # 只有在FC/AJ时才写入 missCount，以保持存档纯净
            if miss_count != -1:
                entry["missCount"] = miss_count
            
            game_data['userMusicDetailList'].append(entry)
            added_records += 1
            
    # 步骤 4: 写出最终文件
    print("\n步骤 3: 正在写出最终合并后的存档文件...")
    try:
        with open(JSON_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            # indent=2 使输出的 JSON 文件格式化，易于阅读
            json.dump(game_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  > 错误: 写入 JSON 文件失败: {e}")
        return

    # 最终总结
    print("\n--- 合并完成 ---")
    print(f"成功添加了 {added_records} 条新成绩。")
    print(f"更新了 {updated_records} 条已有成绩中的最佳记录。")
    print(f"\n成功生成最终存档文件: '{JSON_OUTPUT_FILE}'")


# 当脚本被直接运行时，执行 main() 函数
if __name__ == '__main__':
    main()

# ##############################################################################
# #
# #   Special thanks to Google Gemini for the invaluable assistance in
# #   developing and debugging this script.
# #
# #   License: CC BY-NC-SA 4.0
# #   Coded by Google Gemini, guided and perfected by Tesget
# #
# ##############################################################################
# #
# #                      CHUNITHM Score Merger Script
# #
# ##############################################################################
# #
# #                           Version: V50KFC Final
# #
# # 本脚本由 Google Gemini 倾情敲出，快感谢Google
# # 
# # (模型基于 Gemini 2.5 Pro)
# #
# # --- 使用说明 ---
# #
# # [所需文件]
# #   - JSON 存档: 一份从 RinNet 导出的 JSON 格式 CHUNITHM 存档。
# #                (需要基于 CHUNITHM VERSE 及更新的版本)
# #   - CSV 档案: 一份从“落雪咖啡屋”导出的 CSV 格式的分数列表。
# #
# # [运行步骤]
# #   1. 将本脚本文件 (.py) 与你的 JSON 和 CSV 文件放置在同一个文件夹中。
# #   2. 修改下方 [配置项] 中的文件名，使其与你的文件名完全一致，并且依据落雪导出的分数列表版本（ 2025 or 2026 ）来选择
# #   3. 打开 CMD (命令提示符) 或其他终端工具。
# #   4. 在终端中进入脚本所在的文件夹。
# #   5. 运行命令: python CHUNITHMScoreMerger.py
# #
# # [注意事项]
# #   - 通过命令行运行本脚本需要您的电脑已安装 Python 环境，请自行安装。
# #   - 推荐你使用Visual Studio Code
# #   - Full Chain 有可能会有小问题,请根据实际情况切换开关
# #   - 由于作者只会叫ai修改和为ai提供建议与及帮ai找他没想到的小问题，所以这个脚本如果出了点小问题或者个体差异的话我直接投降喵
# #
# # [免责声明]
# #   - 作者和RinNet服无关，使用该脚本默认你在已阅读过RinNet的警告“虽然这可以工作，但不建议使用此功能” 
# #   - 使用或滥用此脚本导致的账号问题，本人不承担任何责任
# #   - 本脚本的唯一设计目的是为玩家提供一个方便的、用于迁移个人在其他平台游玩时产生的合法、真实的游戏记录的工具。请不要手动修改 CSV 文件来使用本脚本去伪造、上传虚假分数或用于任何形式的作弊行为。请尊重游戏和其他玩家。
# #   - 本脚本会修改您的存档文件，这是一个具有潜在风险的操作。强烈建议您在使用前，务必手动备份一份原始的 JSON 存档文件！ 对于因使用本脚本（或因脚本中可能存在的未知 Bug）而导致的任何数据丢失、存档损坏或其它不可预见的损失，本人不承担任何责任
# #   - 本脚本仅供个人使用，请不要也不能用于任何商业用途
# #
# ##############################################################################

import json
import csv
import os

# --- 配置项 ---
# 请在这里修改你的文件名
JSON_INPUT_FILE = 'chusan_xxxxxxx_exported.json'
CSV_INPUT_FILE = 'chunithm-scores.csv'

# 版本兼容模式开关
# True  = LMN -> VERSE 模式: 用于合并旧版(2025 LUMINOUS)CSV到新版存档 (默认)
# False = VERSE -> VERSE 模式: 用于合并新版(2026 VERSE)CSV到新版存档
LUMINOUS_CSV_MODE = True

# Full Chain 合并开关
# True = 合并 Full Chain 等级 (默认)
# False = 完全不合并 Full Chain 等级
MERGE_FULL_CHAIN = True

# --- 数据映射区 ---
# 定义了如何将 CSV 中的文本数据转换为游戏存档能识别的数字代码

# 评级 (Rank) -> `scoreRank` 字段
RANK_MAP = {
    'd': 0, 'c': 1, 'b': 2, 'bb': 3, 'bbb': 4, 'a': 5, 'aa': 6, 'aaa': 7,
    's': 8, 'sp': 9, 'ss': 10, 'ssp': 11, 'sss': 12, 'sssp': 13
}
# Full Chain 等级 -> `fullChain` 字段
FULL_CHAIN_MAP = {
    "fullchain": 1, "fullchain1": 1, "fullchain2": 2, "fullchain3": 3, "fullchain4": 4
}

# 为两种兼容模式定义不同的通关标签映射表
# 模式 True: 旧版CSV(LMN) -> 新版存档(VERSE) 的“翻译”映射
LAMP_MAP_LMN_TO_VERSE = {
    'failed': 0, 'clear': 1, 'hard': 2,
    'absolute': 3,    # 旧版 Absolute (150血) -> 新版 Brave (3)
    'absolutep': 4,   # 旧版 Absolute+ (50血) -> 新版 Absolute (4)
    'catastrophy': 6
}
# 模式 False: 新版CSV(VERSE) -> 新版存档(VERSE) 的“直接”映射
LAMP_MAP_VERSE_TO_VERSE = {
    'failed': 0, 'clear': 1, 'hard': 2, 'brave': 3,
    'absolute': 4,    # 新版 Absolute -> 4
    'catastrophy': 6
}


# --- 核心功能函数 ---
def preprocess_csv(csv_path, lamp_map):
    """
    第一步：预处理 CSV 文件，为每首歌的每个难度构建一个“最佳成就档案”。
    这个函数会扫描整个 CSV，确保为每首歌都找到历史最佳的各项成就，
    以解决 CSV 中包含同一歌曲的多个不同时期记录的问题。
    """
    best_scores = {}
    print("\n步骤 1: 正在扫描 CSV 并构建最佳成就档案...")

    try:
        # 使用 'utf-8-sig' 编码可以正确处理带有 BOM 的文件（通常由 Windows 程序生成）
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    music_id = int(row['id'])
                    level_index = int(row['level_index'])
                    record_key = (music_id, level_index)

                    # 提取当前行的所有成就数据
                    current_score = int(row['score'])
                    current_rank = row.get('rank', '').strip()
                    
                    # AJ/FC 识别逻辑
                    # 所有 FC/AJ/AJC 信息都来自于 'full_combo' 列
                    fc_col_str = row.get('full_combo', '').strip().lower()
                    
                    # AJ 的判断：只要 'full_combo' 列中包含 "alljustice" 即可
                    current_aj_bool = 'alljustice' in fc_col_str
                    
                    # FC 的判断：只要 'full_combo' 列有任何内容，就算 FC
                    current_fc_bool = bool(fc_col_str)
                    
                    lamp_text = row.get('clear', '').strip().lower()
                    current_lamp_id = lamp_map.get(lamp_text, 0)
                    
                    # 根据开关决定是否处理 Full Chain
                    current_fc_chain_id = 0
                    if MERGE_FULL_CHAIN:
                        current_fc_chain_id = FULL_CHAIN_MAP.get(row.get('full_chain', '').strip().lower(), 0)

                    # 如果是第一次见到这首歌，直接存入档案
                    if record_key not in best_scores:
                        best_scores[record_key] = {
                            'score': current_score, 'rank': current_rank,
                            'aj_bool': current_aj_bool, 'fc_bool': current_fc_bool,
                            'lamp_id': current_lamp_id, 'fc_chain_id': current_fc_chain_id
                        }
                    else:
                        # 如果已存在，则逐项比较并更新为更好的成就
                        entry = best_scores[record_key]
                        if current_score > entry['score']:
                            entry['score'] = current_score
                            entry['rank'] = current_rank
                        
                        # 更新原则：只要历史上有过一次 AJ/FC，就永远记录为 AJ/FC
                        if current_aj_bool:
                            entry['aj_bool'] = True
                        if current_fc_bool:
                            entry['fc_bool'] = True
                        
                        if current_lamp_id > entry['lamp_id']:
                            entry['lamp_id'] = current_lamp_id
                        if MERGE_FULL_CHAIN and current_fc_chain_id > entry['fc_chain_id']:
                            entry['fc_chain_id'] = current_fc_chain_id
                
                except (ValueError, KeyError, TypeError):
                    # 跳过 CSV 中任何格式不正确的行
                    continue
    except Exception as e:
        print(f"  > 错误: 读取 CSV 文件时发生严重错误: {e}")
        return None
    
    print(f"  > 扫描完成！共构建了 {len(best_scores)} 条独立的最佳成就记录。")
    return best_scores

def main():
    """脚本主执行函数"""
    print("--- CHUNITHM 分数合并脚本 (V50KFC Final) ---")

    # 根据开关选择正确的 LAMP_MAP
    if LUMINOUS_CSV_MODE:
        active_lamp_map = LAMP_MAP_LMN_TO_VERSE
        print("  > 兼容模式: 已启动 (旧版CSV -> 新版存档)")
    else:
        active_lamp_map = LAMP_MAP_VERSE_TO_VERSE
        print("  > 兼容模式: 已关闭 (新版CSV -> 新版存档)")

    # 检查输入文件是否存在
    if not all(os.path.exists(f) for f in [JSON_INPUT_FILE, CSV_INPUT_FILE]):
        print("错误: 输入文件缺失。")
        return

    # 步骤 1: 预处理 CSV，获得最佳成就档案
    best_csv_scores = preprocess_csv(CSV_INPUT_FILE, active_lamp_map)
    if best_csv_scores is None:
        return

    # 步骤 2: 读取 JSON 存档
    print("\n步骤 2: 正在读取 JSON 存档并准备合并...")
    base_name = os.path.splitext(JSON_INPUT_FILE)[0]
    JSON_OUTPUT_FILE = f"{base_name}_merged.json"

    try:
        with open(JSON_INPUT_FILE, 'r', encoding='utf-8') as f:
            game_data = json.load(f)
    except Exception as e:
        print(f"  > 错误: 读取 JSON 文件失败: {e}")
        return

    # 确保 JSON 结构正确
    if 'userMusicDetailList' not in game_data:
        print("  > 错误: 无法在 JSON 存档中找到 'userMusicDetailList'。")
        return
    
    # 为了快速查找，将列表转换为以 (歌曲ID, 难度) 为键的字典
    music_list = game_data['userMusicDetailList']
    music_map = {(item['musicId'], item['level']): item for item in music_list}
    print("  > 读取成功，开始智能合并...")

    updated_records, added_records = 0, 0
    
    # 步骤 3: 使用最佳成就档案进行智能合并
    for record_key, best_data in best_csv_scores.items():
        music_id, level_index = record_key
        
        # 从档案中提取各项最佳成就
        score = best_data['score']
        rank_str = best_data['rank']
        aj_bool = best_data['aj_bool']
        fc_bool = best_data['fc_bool']
        lamp_id = best_data['lamp_id']
        fc_chain_id = best_data['fc_chain_id']

        # 最终逻辑：AJ 必然包含 FC
        if aj_bool:
            fc_bool = True

        # 判断是更新现有记录，还是添加新记录
        if record_key in music_map:
            # --- 更新现有记录 ---
            score_detail = music_map[record_key]
            has_update = False

            # 逐项比较，只有在 CSV 中的成就更好时才更新
            if score > score_detail.get('scoreMax', 0):
                score_detail['scoreMax'] = score
                # [最终修正] 更新 scoreRank 字段
                score_detail['scoreRank'] = RANK_MAP.get(rank_str.lower(), score_detail.get('scoreRank', 0))
                has_update = True
            
            if lamp_id > score_detail.get('isSuccess', 0):
                score_detail['isSuccess'] = lamp_id
                has_update = True
            
            if fc_bool and not score_detail.get('isFullCombo', False):
                score_detail['isFullCombo'] = True
                score_detail['missCount'] = 0
                has_update = True
            
            if aj_bool and not score_detail.get('isAllJustice', False):
                score_detail['isAllJustice'] = True
                score_detail['isFullCombo'] = True # 强制激活 FC
                score_detail['missCount'] = 0
                has_update = True
            
            # 根据开关决定是否更新 Full Chain
            if MERGE_FULL_CHAIN and fc_chain_id > score_detail.get('fullChain', 0):
                score_detail['fullChain'] = fc_chain_id
                has_update = True
            
            # 如果有任何更新，增加游戏次数
            if has_update:
                updated_records += 1
                score_detail['playCount'] = score_detail.get('playCount', 0) + 1
        
        else:
            # --- 添加新记录 ---
            miss_count = 0 if fc_bool else -1
            # 根据开关决定新纪录的 Full Chain 值
            final_fc_chain_id = fc_chain_id if MERGE_FULL_CHAIN else 0
            
            entry = {
                "musicId": music_id, "level": level_index, "playCount": 1,
                "scoreMax": score, 
                "scoreRank": RANK_MAP.get(rank_str.lower(), 0),
                "isFullCombo": fc_bool, "isAllJustice": aj_bool,
                "isSuccess": lamp_id,
                "fullChain": final_fc_chain_id, "ext1": 0,
                "maxComboCount": 0, "maxChain": 0, "isLock": False, "theoryCount": 0
            }
            # 只有在FC/AJ时才写入 missCount，以保持存档纯净
            if miss_count != -1:
                entry["missCount"] = miss_count
            
            game_data['userMusicDetailList'].append(entry)
            added_records += 1
            
    # 步骤 4: 写出最终文件
    print("\n步骤 3: 正在写出最终合并后的存档文件...")
    try:
        with open(JSON_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            # indent=2 使输出的 JSON 文件格式化，易于阅读
            json.dump(game_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"  > 错误: 写入 JSON 文件失败: {e}")
        return

    # 最终总结
    print("\n--- 合并完成 ---")
    print(f"成功添加了 {added_records} 条新成绩。")
    print(f"更新了 {updated_records} 条已有成绩中的最佳记录。")
    print(f"\n成功生成最终存档文件: '{JSON_OUTPUT_FILE}'")


# 当脚本被直接运行时，执行 main() 函数
if __name__ == '__main__':
    main()

# ##############################################################################
# #
# #   Special thanks to Google Gemini for the invaluable assistance in
# #   developing and debugging this script.
# #
# #   License: CC BY-NC-SA 4.0
# #   Coded by Google Gemini, guided and perfected by Tesget
# ##############################################################################