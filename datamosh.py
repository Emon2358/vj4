import subprocess
import os
import random
import sys
import re # URLからファイル名を抽出するために追加

def download_niconico_video(url, output_dir="videos"):
    """
    yt-dlpを使ってニコニコ動画をダウンロードします。

    Args:
        url (str): ニコニコ動画のURL。
        output_dir (str): ダウンロードした動画を保存するディレクトリ。

    Returns:
        str: ダウンロードされた動画ファイルのパス、またはエラーの場合はNone。
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # yt-dlpの出力テンプレートを設定
    # %(title)s は動画のタイトル、%(ext)s は拡張子
    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
    
    print(f"ニコニコ動画をダウンロード中: {url}...")
    try:
        # yt-dlp を実行して動画をダウンロード
        # --output: 出力ファイル名を指定
        # --format bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best: MP4形式で最高品質の動画と音声を結合、または最高のMP4形式、または最高の品質を選択
        # --merge-output-format mp4: 結合された出力の形式をmp4に設定
        result = subprocess.run([
            "yt-dlp",
            "--output", output_template,
            "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            url
        ], check=True, capture_output=True, text=True)
        print("yt-dlp出力:\n", result.stdout)

        # yt-dlpの出力からダウンロードされたファイルパスを解析
        # [download] Destination: ... の行を探す
        match = re.search(r'\[download\] Destination: (.+)', result.stdout)
        if match:
            downloaded_file_path = match.group(1).strip()
            print(f"ダウンロード完了: {downloaded_file_path}")
            return downloaded_file_path
        else:
            print("エラー: ダウンロードされたファイルパスをyt-dlpの出力から解析できませんでした。")
            print("yt-dlpの完全な出力:\n", result.stdout)
            return None

    except subprocess.CalledProcessError as e:
        print(f"yt-dlpエラー: {e.stderr}")
        return None
    except Exception as e:
        print(f"ダウンロード中に予期せぬエラーが発生しました: {e}")
        return None

def datamosh_video(input_video_path, output_video_path, glitches_to_apply=5, glitch_strength=5000):
    """
    PythonとFFmpegを使って動画にデータモッシングを施します。

    Args:
        input_video_path (str): 入力動画ファイルのパス。
        output_video_path (str): 出力動画ファイルのパス。
        glitches_to_apply (int): 適用するグリッチの回数。
        glitch_strength (int): グリッチの強さ（バイト数）。数値が大きいほど破損が大きくなります。
    """

    if not os.path.exists(input_video_path):
        print(f"エラー: 入力ファイルが見つかりません - {input_video_path}")
        sys.exit(1) # スクリプトを終了

    # 一時ファイルのパスを設定
    temp_inter_video = "temp_inter.avi"
    temp_glitched_video = "temp_glitched.avi"

    print("ステップ1: Iフレーム間隔を広く設定し、AVIに変換中...")
    try:
        subprocess.run([
            "ffmpeg", "-i", input_video_path,
            "-vf", "setpts=PTS/1.0",
            "-q:v", "0",
            "-g", "99999", # Iフレーム間隔を非常に大きく設定
            "-f", "avi", temp_inter_video
        ], check=True, capture_output=True, text=True)
        print("一時AVIファイル作成完了。")
    except subprocess.CalledProcessError as e:
        print(f"FFmpegエラー (ステップ1): {e.stderr}")
        if os.path.exists(temp_inter_video):
            os.remove(temp_inter_video)
        sys.exit(1)

    print(f"ステップ2: バイナリ破損を {glitches_to_apply} 回適用中...")
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
            start_offset = random.randint(min_offset, video_size - glitch_strength - 1)
            if start_offset < 0:
                start_offset = 0
            end_offset = start_offset + glitch_strength

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

    print("ステップ3: 破損したAVIファイルを最終出力形式に変換中...")
    try:
        subprocess.run([
            "ffmpeg", "-i", temp_glitched_video,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "23",
            "-y",
            output_video_path
        ], check=True, capture_output=True, text=True)
        print(f"データモッシュ完了: {output_video_path}")
    except subprocess.CalledProcessError as e:
        print(f"FFmpegエラー (ステップ3): {e.stderr}")
        sys.exit(1)
    finally:
        if os.path.exists(temp_inter_video):
            os.remove(temp_inter_video)
        if os.path.exists(temp_glitched_video):
            os.remove(temp_glitched_video)
        print("一時ファイルを削除しました。")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("使用法:")
        print("  ファイルパスからデータモッシュ: python datamosh.py <入力ファイル名> <出力ファイル名> [グリッチ回数] [グリッチ強度]")
        print("  ニコニコ動画URLからデータモッシュ: python datamosh.py --url <ニコニコ動画URL> <出力ファイル名> [グリッチ回数] [グリッチ強度]")
        sys.exit(1)

    input_is_url = False
    input_source = sys.argv[1] # ファイルパスまたは --url
    output_file_index = 2 # 出力ファイルのsys.argvインデックス

    if input_source == "--url":
        input_is_url = True
        if len(sys.argv) < 4:
            print("エラー: --url オプションを使用する場合は、ニコニコ動画URLと出力ファイル名を指定する必要があります。")
            sys.exit(1)
        niconico_url = sys.argv[2]
        output_file = sys.argv[3]
        glitches_index = 4
        strength_index = 5
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        glitches_index = 3
        strength_index = 4

    glitches = int(sys.argv[glitches_index]) if len(sys.argv) > glitches_index else 10 # デフォルトは10回
    strength = int(sys.argv[strength_index]) if len(sys.argv) > strength_index else 8000 # デフォルトは8000バイト

    if input_is_url:
        # ダウンロードディレクトリを一時的に設定
        download_dir = "downloaded_videos"
        downloaded_path = download_niconico_video(niconico_url, download_dir)
        if downloaded_path:
            datamosh_video(downloaded_path, output_file, glitches_to_apply=glitches, glitch_strength=strength)
            # ダウンロードした一時ファイルを削除
            if os.path.exists(downloaded_path):
                os.remove(downloaded_path)
                print(f"一時ダウンロードファイル {downloaded_path} を削除しました。")
        else:
            print("動画のダウンロードに失敗しました。データモッシュをスキップします。")
            sys.exit(1)
    else:
        datamosh_video(input_file, output_file, glitches_to_apply=glitches, glitch_strength=strength)

