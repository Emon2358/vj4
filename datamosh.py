import subprocess
import os
import random
import sys

def datamosh_video(input_video_path, output_video_path, glitches_to_apply=5, glitch_strength=5000):
    """
    PythonとFFmpegを使って動画にデータモッシングを施します。
    動画の長さを短くすることなく、指定された回数と強度で破損を適用します。

    Args:
        input_video_path (str): 入力動画ファイルのパス。
        output_video_path (str): 出力動画ファイルのパス。
        glitches_to_apply (int): 適用するグリッチの回数。
        glitch_strength (int): 各グリッチで破損させるバイト数。数値が大きいほど破損が大きくなります。
    """

    if not os.path.exists(input_video_path):
        print(f"エラー: 入力ファイルが見つかりません - {input_video_path}")
        sys.exit(1) # スクリプトを終了

    # 一時ファイルのパスを設定
    temp_inter_video = "temp_inter.avi"
    temp_glitched_video = "temp_glitched.avi"

    print("--- ステップ1: Iフレーム間隔を広く設定し、AVIに変換中（データモッシュ準備） ---")
    try:
        # FFmpegコマンド: 入力動画をAVI形式に変換し、Iフレーム間隔を非常に大きく設定します。
        # `-vf setpts=PTS/1.0`: 動画のタイムスタンプを維持し、長さを変更しないようにします。
        # `-q:v 0`: 変換時のビデオ品質を最高に設定し、劣化を最小限に抑えます。
        # `-g 99999`: Iフレーム間隔を非常に大きく設定し、P/Bフレームを増やしてデータモッシュの効果を高めます。
        # `-f avi`: 出力フォーマットをAVIに指定します。
        subprocess.run([
            "ffmpeg", "-i", input_video_path,
            "-vf", "setpts=PTS/1.0", # 動画の長さを維持
            "-q:v", "0",             # 品質を最高に近く設定
            "-g", "99999",           # Iフレーム間隔を非常に大きく設定
            "-f", "avi", temp_inter_video
        ], check=True, capture_output=True, text=True)
        print("一時AVIファイル作成完了。")
    except subprocess.CalledProcessError as e:
        print(f"FFmpegエラー (ステップ1): {e.stderr}")
        if os.path.exists(temp_inter_video):
            os.remove(temp_inter_video)
        sys.exit(1)

    print(f"--- ステップ2: バイナリ破損を {glitches_to_apply} 回適用中 ---")
    try:
        with open(temp_inter_video, "rb") as f:
            video_data = bytearray(f.read())

        video_size = len(video_data)
        print(f"ビデオデータサイズ: {video_size} バイト")

        # 少なくともビデオデータの5%はスキップする（ヘッダー等の破損を避けるため）
        min_offset = int(video_size * 0.05)
        if min_offset > video_size - glitch_strength - 1:
            min_offset = 0 # データが小さい場合はスキップしない

        for _ in range(glitches_to_apply):
            # ヘッダー領域を避け、動画データ範囲内でランダムな開始オフセットを選択
            start_offset = random.randint(min_offset, video_size - glitch_strength - 1)
            if start_offset < 0:
                start_offset = 0
            end_offset = start_offset + glitch_strength

            # 破損させるバイト数をランダムなデータで上書き
            for i in range(start_offset, min(end_offset, video_size)):
                video_data[i] = random.randint(0, 255)

            print(f"  破損適用: オフセット {start_offset} から {end_offset} ({glitch_strength} バイト)")

        with open(temp_glitched_video, "wb") as f:
            f.write(video_data)
        print("バイナリ破損適用完了。")

    except Exception as e:
        print(f"ファイル処理エラー (ステップ2): {e}")
        if os.path.exists(temp_inter_video):
            os.remove(temp_inter_video)
        if os.path.exists(temp_glitched_video):
            os.remove(temp_glitched_video)
        sys.exit(1)

    print("--- ステップ3: 破損したAVIファイルを最終出力形式に変換中 ---")
    try:
        # FFmpegコマンド: 破損したAVIファイルを最終的なMP4形式に再エンコードします。
        # `-c:v libx264`: H.264ビデオコーデックを使用します。
        # `-preset medium`: エンコード速度と圧縮率のバランスを取ります。
        # `-crf 23`: 品質設定。数値が小さいほど高品質ですが、ファイルサイズは大きくなります。
        # `-y`: 既存の出力ファイルを上書きします。
        # `-vsync passthrough`: 動画の同期をパススルーし、長さを維持します。
        # `-pix_fmt yuv420p`: 一般的なピクセルフォーマットを指定します。
        subprocess.run([
            "ffmpeg", "-i", temp_glitched_video,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-vsync", "passthrough", # 動画の長さを維持
            "-pix_fmt", "yuv420p",
            "-y",
            output_video_path
        ], check=True, capture_output=True, text=True)
        print(f"データモッシュ完了: {output_video_path}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpegエラー (ステップ3): {e.stderr}")
        sys.exit(1)
    finally:
        # 一時ファイルをクリーンアップ
        if os.path.exists(temp_inter_video):
            os.remove(temp_inter_video)
        if os.path.exists(temp_glitched_video):
            os.remove(temp_glitched_video)
        print("一時ファイルを削除しました。")

if __name__ == "__main__":
    # コマンドライン引数から入力ファイル名と出力ファイル名を取得
    if len(sys.argv) < 3:
        print("使用法: python datamosh.py <入力ファイル名> <出力ファイル名> [グリッチ回数] [グリッチ強度]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]
    # コマンドライン引数が指定されない場合、デフォルト値を使用
    glitches = int(sys.argv[3]) if len(sys.argv) > 3 else 10 # デフォルトは10回
    strength = int(sys.argv[4]) if len(sys.argv) > 4 else 8000 # デフォルトは8000バイト

    datamosh_video(input_file, output_file, glitches_to_apply=glitches, glitch_strength=strength)
