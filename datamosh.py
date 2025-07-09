import subprocess
import os
import random
import sys

def datamosh_video_extreme_fast(input_video_path, output_video_path, total_glitch_percentage=0.1, num_glitch_blocks=100):
    """
    PythonとFFmpegを使って、超絶極限まで強力にデータモッシングを行い、生成速度を極限まで早くします。

    Args:
        input_video_path (str): 入力動画ファイルのパス。
        output_video_path (str): 出力動画ファイルのパス。
        total_glitch_percentage (float): 動画データ全体に対して破壊するバイトの割合 (0.0 - 1.0)。
                                         0.1 は動画データの10%を破壊することを示します。
        num_glitch_blocks (int): 破壊を行うブロックの数。多いほど破壊が細かくなります。
    """

    if not os.path.exists(input_video_path):
        print(f"エラー: 入力ファイルが見つかりません - {input_video_path}")
        sys.exit(1)

    temp_avi_path = "temp_fast_mosh.avi"
    temp_glitched_avi_path = "temp_glitched_fast_mosh.avi"

    print("--- ステップ1: 高速・高Iフレーム間隔でAVIに変換中（データモッシュ準備） ---")
    try:
        # Iフレーム間隔を非常に大きくし（P/Bフレームを増やす）、最高品質でAVIに変換
        # オーディオはコピーし、時間と速度を最優先
        subprocess.run([
            "ffmpeg", "-i", input_video_path,
            "-c:v", "rawvideo", # AVIへの最速変換 (非圧縮、巨大ファイルになります)
            "-pix_fmt", "yuv420p", # 一般的なピクセルフォーマット
            "-g", "999999", # Iフレーム間隔を極限まで大きく
            "-vsync", "passthrough", # 動画の同期をパススルー（速度優先）
            "-f", "avi", temp_avi_path
        ], check=True, capture_output=True, text=True)
        print(f"一時AVIファイル作成完了: {temp_avi_path}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpegエラー (ステップ1): {e.stderr}")
        if os.path.exists(temp_avi_path): os.remove(temp_avi_path)
        sys.exit(1)

    print("--- ステップ2: バイナリデータの極限破壊中 ---")
    try:
        with open(temp_avi_path, "rb") as f:
            video_data = bytearray(f.read())

        video_size = len(video_data)
        print(f"ビデオデータサイズ: {video_size} バイト")

        # AVIヘッダーを避けるためのオフセット (経験的な値、変更可)
        # AVIヘッダーは通常、もっと小さいが、安全を見て大きめに設定
        header_offset_safety = 1024 * 10 # 最初の10KBは避ける

        if video_size <= header_offset_safety:
            print("警告: 動画データが小さすぎるため、ヘッダー保護を適用できません。")
            header_offset_safety = 0

        # 破壊する総バイト数を計算
        bytes_to_glitch = int(video_size * total_glitch_percentage)
        print(f"総破壊バイト数: {bytes_to_glitch} バイト ({total_glitch_percentage*100:.2f}%)")

        # 各ブロックで破壊するバイト数
        glitch_strength_per_block = bytes_to_glitch // num_glitch_blocks
        if glitch_strength_per_block <= 0:
            glitch_strength_per_block = 1 # 少なくとも1バイトは破壊

        for _ in range(num_glitch_blocks):
            # ヘッダー領域を避け、動画データ範囲内でランダムな開始オフセットを選択
            max_start_offset = video_size - glitch_strength_per_block - 1
            if max_start_offset < header_offset_safety:
                start_offset = header_offset_safety # 破壊できる場所がなければヘッダー直後から
            else:
                start_offset = random.randint(header_offset_safety, max_start_offset)
            
            end_offset = start_offset + glitch_strength_per_block

            # 破損させるバイト数をランダムなデータで上書き
            for i in range(start_offset, min(end_offset, video_size)):
                video_data[i] = random.randint(0, 255)

            # print(f"  破損適用: オフセット {start_offset} から {end_offset} ({glitch_strength_per_block} バイト)")

        with open(temp_glitched_avi_path, "wb") as f:
            f.write(video_data)
        print("バイナリ破損適用完了。")

    except Exception as e:
        print(f"ファイル処理エラー (ステップ2): {e}")
        if os.path.exists(temp_avi_path): os.remove(temp_avi_path)
        if os.path.exists(temp_glitched_avi_path): os.remove(temp_glitched_avi_path)
        sys.exit(1)

    print("--- ステップ3: 破損したAVIファイルを最終出力形式に超高速変換中 ---")
    try:
        # 超高速エンコード設定
        subprocess.run([
            "ffmpeg", "-i", temp_glitched_avi_path,
            "-c:v", "libx264",         # H.264コーデック
            "-preset", "ultrafast",    # 最速プリセット
            "-crf", "30",              # 品質を犠牲にして速度優先（高いほど低品質）
            "-tune", "zerolatency",    # 遅延最小化（速度向上に寄与）
            "-vsync", "passthrough",   # 同期をパススルー
            "-pix_fmt", "yuv420p",     # 一般的なピクセルフォーマット
            "-map", "0:v:0",           # 最初のビデオストリームのみをマップ (音声は含めないか、別途処理)
            "-an",                     # 音声ストリームを削除
            "-y",                      # 既存の出力ファイルを上書き
            output_video_path
        ], check=True, capture_output=True, text=True)
        print(f"データモッシュ完了: {output_video_path}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpegエラー (ステップ3): {e.stderr}")
        sys.exit(1)
    finally:
        # 一時ファイルをクリーンアップ
        if os.path.exists(temp_avi_path): os.remove(temp_avi_path)
        if os.path.exists(temp_glitched_avi_path): os.remove(temp_glitched_avi_path)
        print("一時ファイルを削除しました。")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用法: python datamosh.py <入力ファイル名> <出力ファイル名> [総破壊割合(0.0-1.0)] [破壊ブロック数]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    total_glitch_percentage = float(sys.argv[3]) if len(sys.argv) > 3 else 0.1 # デフォルトは10%の破壊
    num_glitch_blocks = int(sys.argv[4]) if len(sys.argv) > 4 else 100 # デフォルトは100ブロックに分割して破壊

    datamosh_video_extreme_fast(input_file, output_file, total_glitch_percentage, num_glitch_blocks)
