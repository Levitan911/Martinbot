import sys
import struct
import win32con
import win32clipboard
from pathlib import Path
from conf.settings import config

STICKERS_DIR = config.martin.general.STICKERS_DIR


def copy_files_to_clipboard(target_dir_relative_path=STICKERS_DIR):
    """
    将文件路径列表复制到剪贴板，实现类似“复制文件”操作。
    
    参数:
      target_dir_relative_path: 文件目录，相对路径
    """
    file_paths = [str(f_p.resolve()) for f_p in Path(target_dir_relative_path).iterdir() if f_p.is_file()]

    # 构造文件列表字符串：
    # 每个文件路径后面以 '\0' 结束，最后再添加一个额外的 '\0'
    file_list = "\0".join(file_paths) + "\0\0"
    # Windows 剪贴板要求使用 Unicode 格式（utf-16le 编码）
    file_list_bytes = file_list.encode("utf-16le")
    
    # 构造 DROPFILES 结构体
    # 结构体定义:
    # typedef struct _DROPFILES {
    #   DWORD pFiles;   // 从结构体起始到文件列表数据的偏移字节数，一般为20
    #   POINT pt;       // 拖放时的坐标（这里设为0）
    #   BOOL fNC;       // 非客户区标志（设为0）
    #   BOOL fWide;     // 是否为 Unicode 格式，非0表示 Unicode（设为1）
    # } DROPFILES;
    #
    # 使用 struct.pack 进行打包，注意使用小端格式 "<"
    dropfiles = struct.pack("<IiiII", 20, 0, 0, 0, 1)
    
    # 将结构体和文件列表数据拼接
    data = dropfiles + file_list_bytes
    
    # 打开并清空剪贴板，然后设置 CF_HDROP 数据格式（用于文件拖放操作）
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_HDROP, data)
    
    # 同时设置“Preferred DropEffect”格式，指定复制（1：复制；0：剪切）
    cf_drop_effect = win32clipboard.RegisterClipboardFormat("Preferred DropEffect")
    win32clipboard.SetClipboardData(cf_drop_effect, struct.pack("<I", 1))
    
    win32clipboard.CloseClipboard()


def main():
    if len(sys.argv) != 2:
        print("Please provide the image path.")
        sys.exit(1)

    file_image = sys.argv[1]
    files = [file_image]
    copy_files_to_clipboard(files)
    print("文件已复制到剪贴板，可在资源管理器中粘贴。")


if __name__ == '__main__':
    copy_files_to_clipboard()
    print("文件已复制到剪贴板，可在资源管理器中粘贴。")
