import subprocess
import os
import random
import sys
import re

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

    output_template = os.path.join(output_dir, "%(title)s.%(ext)s")
    
    print(f"ニコニコ動画をダウンロード中: {url}...")
    try:
        # --print filepath: ダウンロード後にファイルの絶対パスを出力
        # --verbose: 詳細なログを出力 (デバッグ用)
        # --no-simulate: シミュレーションモードを無効化
        # --output: 出力ファイル名を指定
        # --format bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best: MP4形式で最高品質の動画と音声を結合、または最高のMP4形式、または最高の品質を選択
        # --merge-output-format mp4: 結合された出力の形式をmp4に設定
        result = subprocess.run([
            "yt-dlp",
            "--output", output_template,
            "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--merge-output-format", "mp4",
            "--print", "filepath", # ダウンロードされたファイルの絶対パスを出力
            "--verbose", # デバッグのために詳細ログを追加
            url
        ], check=True, capture_output=True, text=True)
        
        # yt-dlpのstdoutには、--print filepathで指定されたパスが含まれるはず
        # 最後の行がfilepathであることが多いが、念のため正規表現で抽出
        downloaded_file_path_match = re.search(r'^(.*?)\n?$', result.stdout.strip().split('\n')[-1])
        downloaded_file_path = downloaded_file_path_match.group(1) if downloaded_file_path_match else ""

        # 実際にファイルが存在するか確認
        if os.path.exists(downloaded_file_path):
            print(f"ダウンロード完了: {downloaded_file_path}")
            print(f"DOWNLOADED_PATH:{downloaded_file_path}") # GitHub Actionsでパースするためのマーカー
            return downloaded_file_path
        else:
            print(f"エラー: yt-dlpは完了しましたが、ファイルが見つかりません: {downloaded_file_path}")
            print("yt-dlpの完全な出力:\n", result.stdout)
            print("yt-dlpのエラー出力:\n", result.stderr)
            print("ERROR:File not found after download") # GitHub Actionsでパースするためのマーカー
            return None

    except subprocess.CalledProcessError as e:
        print(f"yt-dlpエラー: {e.stderr}")
        print(f"ERROR:yt-dlp failed with exit code {e.returncode}") # GitHub Actionsでパースするためのマーカー
        return None
    except Exception as e:
        print(f"ダウンロード中に予期せぬエラーが発生しました: {e}")
        print(f"ERROR:Unexpected error during download: {e}") # GitHub Actionsでパースするためのマーカー
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
    # コマンドライン引数の解析をより堅牢にする
    args = sys.argv[1:]
    
    input_file = None
    output_file = None
    niconico_url = None
    glitches = 10
    strength = 8000

    i = 0
    while i < len(args):
        if args[i] == "--url":
            niconico_url = args[i+1]
            i += 2
        elif args[i] == "--glitches":
            glitches = int(args[i+1])
            i += 2
        elif args[i] == "--strength":
            strength = int(args[i+1])
            i += 2
        else:
            # 残りの引数をファイルパスとして扱う
            if input_file is None:
                input_file = args[i]
            elif output_file is None:
                output_file = args[i]
            i += 1

    # --url が指定されている場合は、出力ファイルが必須
    if niconico_url and not output_file:
        print("エラー: --url オプションを使用する場合は、出力ファイル名を指定する必要があります。")
        sys.exit(1)
    # --url もファイルパスも指定されていない場合
    if not niconico_url and not input_file:
        print("使用法:")
        print("  ファイルパスからデータモッシュ: python datamosh.py <入力ファイル名> <出力ファイル名> [--glitches <回数>] [--strength <強度>]")
        print("  ニコニコ動画URLからデータモッシュ: python datamosh.py --url <ニコニコ動画URL> <出力ファイル名> [--glitches <回数>] [--strength <強度>]")
        sys.exit(1)
    
    # ローカルファイルパスが指定されている場合は、出力ファイルが必須
    if input_file and not output_file:
        print("エラー: ローカルファイルパスを指定する場合は、出力ファイル名を指定する必要があります。")
        sys.exit(1)

    if niconico_url:
        download_dir = "downloaded_videos"
        downloaded_path = download_niconico_video(niconico_url, download_dir)
        if downloaded_path:
            # ダウンロードが成功した場合のみデータモッシュを実行
            # 出力ファイル名は、ダウンロードされたファイル名に基づいて生成
            input_filename_no_ext = os.path.splitext(os.path.basename(downloaded_path))[0]
            final_output_file = os.path.join(download_dir, f"{input_filename_no_ext}_datamoshed.mp4")
            
            datamosh_video(downloaded_path, final_output_file, glitches_to_apply=glitches, glitch_strength=strength)
            
            # ダウンロードした一時ファイルを削除 (データモッシュされたファイルと異なる場合のみ)
            if os.path.exists(downloaded_path) and downloaded_path != final_output_file:
                os.remove(downloaded_path)
                print(f"一時ダウンロードファイル {downloaded_path} を削除しました。")
        else:
            print("動画のダウンロードに失敗しました。データモッシュをスキップします。")
            sys.exit(1)
    elif input_file:
        datamosh_video(input_file, output_file, glitches_to_apply=glitches, glitch_strength=strength)
