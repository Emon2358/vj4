import subprocess
import os
import random
import sys
import re

def download_niconico_video(url, output_dir="videos", cookies_file_path=None):
    """
    yt-dlpを使ってニコニコ動画をダウンロードします。

    Args:
        url (str): ニコニコ動画のURL。
        output_dir (str): ダウンロードした動画を保存するディレクトリ。
        cookies_file_path (str, optional): クッキーファイルのパス。指定された場合、yt-dlpで使用されます。

    Returns:
        str: ダウンロードされた動画ファイルのパス、またはエラーの場合はNone。
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # URLから動画IDを抽出し、ファイル名に使用
    # sm, nm, so 形式のIDをサポート
    video_id_match = re.search(r'(sm|nm|so)(\d+)', url)
    if video_id_match:
        # 抽出したIDをベースファイル名として使用 (例: sm12345)
        base_filename = video_id_match.group(0)
    else:
        # IDが見つからない場合は、汎用名にする
        base_filename = "niconico_video"

    # ダウンロードされるファイルの正確な出力パスを定義
    # yt-dlpは自動的に正しい拡張子を付与するため、ここでは.mp4を仮定
    download_target_path = os.path.join(output_dir, f"{base_filename}.mp4")

    print(f"ニコニコ動画をダウンロード中: {url}...")
    cmd = [
        "yt-dlp",
        url,
        "--output", download_target_path, # 正確な出力パスを指定
        "--format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "--verbose", # デバッグのために詳細ログを追加
    ]
    if cookies_file_path and os.path.exists(cookies_file_path):
        cmd.extend(["--cookies", cookies_file_path])
        print(f"クッキーファイル {cookies_file_path} を使用します。")
    else:
        print("クッキーファイルは使用しません。")

    try:
        # yt-dlpを実行し、ダウンロードターゲットパスにファイルを保存
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        # yt-dlpが実際にファイルをダウンロードしたか、指定したパスにファイルが存在するか確認
        if os.path.exists(download_target_path):
            print(f"ダウンロード完了: {download_target_path}")
            print(f"DOWNLOADED_PATH:{download_target_path}") # GitHub Actionsでパースするためのマーカー
            return download_target_path
        else:
            print(f"エラー: yt-dlpは完了しましたが、ファイルが見つかりません: {download_target_path}")
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
    
    input_source_arg = None # これは最初の位置引数（ファイルパス、URL、またはID）
    final_output_path_arg = None # これは2番目の位置引数（希望する出力ファイル）
    glitches = 10
    strength = 8000
    cookies_file = "cookies.txt" # デフォルトのクッキーファイルパス（スクリプト実行ディレクトリからの相対パス）

    i = 0
    while i < len(args):
        if args[i] == "--glitches":
            glitches = int(args[i+1])
            i += 2
        elif args[i] == "--strength":
            strength = int(args[i+1])
            i += 2
        elif args[i] == "--cookies-file":
            cookies_file = args[i+1]
            i += 2
        else:
            # オプションではない最初の引数は入力ソース
            # オプションではない2番目の引数は出力ファイル
            if input_source_arg is None:
                input_source_arg = args[i]
            elif final_output_path_arg is None:
                final_output_path_arg = args[i]
            i += 1

    if not input_source_arg or not final_output_path_arg:
        print("使用法:")
        print("  ファイルパスからデータモッシュ: python datamosh.py <入力ファイル名> <出力ファイル名> [--glitches <回数>] [--strength <強度>]")
        print("  ニコニコ動画URL/IDからデータモッシュ: python datamosh.py <ニコニコ動画URLまたはID> <出力ファイル名> [--glitches <回数>] [--strength <強度>] [--cookies-file <パス>]")
        sys.exit(1)

    # input_source_argがURLかニコニコ動画IDかを判断
    is_niconico_input = False
    niconico_url_to_download = None
    
    if input_source_arg.startswith("http://") or input_source_arg.startswith("https://"):
        niconico_url_to_download = input_source_arg
        if "nicovideo.jp/watch/" in input_source_arg:
            is_niconico_input = True
    elif re.match(r'^(sm|nm|so)\d+$', input_source_arg): # ニコニコ動画ID (例: sm9) かどうかを確認
        niconico_url_to_download = f"https://www.nicovideo.jp/watch/{input_source_arg}"
        is_niconico_input = True

    if is_niconico_input:
        download_dir = "downloaded_videos_temp" # ダウンロード用の一時ディレクトリを使用
        downloaded_path = download_niconico_video(niconico_url_to_download, download_dir, cookies_file_path=cookies_file)
        
        if downloaded_path:
            # ダウンロードされた動画を最終出力パスにデータモッシュ
            datamosh_video(downloaded_path, final_output_path_arg, glitches_to_apply=glitches, glitch_strength=strength)
            
            # ダウンロードした一時ファイルをクリーンアップ
            if os.path.exists(downloaded_path):
                os.remove(downloaded_path)
                print(f"一時ダウンロードファイル {downloaded_path} を削除しました。")
            
            # 一時ダウンロードディレクトリが空になったら削除
            if os.path.exists(download_dir) and not os.listdir(download_dir):
                os.rmdir(download_dir)
                print(f"空のダウンロードディレクトリ {download_dir} を削除しました。")

        else:
            print("動画のダウンロードに失敗しました。データモッシュをスキップします。")
            sys.exit(1)
    else: # ローカルファイルパスと仮定
        datamosh_video(input_source_arg, final_output_path_arg, glitches_to_apply=glitches, glitch_strength=strength)

