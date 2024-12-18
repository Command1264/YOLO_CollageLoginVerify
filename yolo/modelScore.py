import tkinter as tk
from tkinter import ttk
from tkinter import messagebox

import cv2 as cv
from PIL import Image, ImageTk
import json, os

model_ans_index = 0

model_file_path = "./testModel/test1-YOLO11X-google-best.pt/ans.json"
human_file_path = "./testModel/test1-YOLO11X-google-best.pt/human_ans.json"

edit_flag = False

show_image_file_name = "image"

root_path = "./TestData/"


def page_up_event():
    global all_data_index

    if all_data_index.get() <= 0: return
    all_data_index.set(all_data_index.get() - 1)

    change_display()

def page_down_event():
    global all_data_index, all_data_list

    if all_data_index.get() >= len(all_data_list) - 1: return
    all_data_index.set(all_data_index.get() + 1)

    change_display()

def page_to_event():
    global all_data_index

    tmp_str = page_entry_str.get()
    if not tmp_str.isdigit(): return

    tmp_number = min(max(int(page_entry_str.get()) - 1, 0), len(all_data_list) - 1)
    all_data_index.set(tmp_number)

    change_display()



def get_file_name_number(file_name):
    return file_name.split(".")[0].split("-")[-1]



def init_page():
    global show_image_file_name, all_data_index, all_data_list
    show_image_file_name = not_tagged_list[0]
    tmp_index = all_data_list.index(show_image_file_name)
    if tmp_index == -1: return
    all_data_index.set(tmp_index)
    change_display()



def change_display():
    global not_tagged_list, show_image_file_name, human_ans, all_data_index, all_data_list
    global human_ans_dict
    index = all_data_index.get()
    show_image_file_name = all_data_list[index]
    ans = model_ans_dict.get(show_image_file_name, None)
    human_ans.set(human_ans_dict.get(show_image_file_name, ""))


    not_ans_count = len(all_data_list) - len(human_ans_dict)
    percent = int((len(human_ans_dict)) / len(all_data_list) * 100)
    progress_bar_percent_str.set(f"{percent}%")
    progress_bar['value'] = percent

    # progress_bar_str.set(f"{percent}% [{'|' * int(percent // 2)}{' ' * (int(not_ans_count // 200) - int(percent // 2))}] {percent}%")

    all_page_label.config(
        text = f"{(index + 1)}/{len(all_data_list)}"
    )

    page_up_button.config(state = tk.NORMAL if index > 0 else tk.DISABLED)
    page_down_button.config(state = tk.NORMAL if index < len(all_data_list) - 1 else tk.DISABLED)

    if ans is not None:
        ans_label.config(text = ans)

    yes_button.config(
        state =
            tk.NORMAL
            if human_ans.get() == "" or len(human_ans.get().strip()) != 4
            else
            tk.DISABLED
    )
    page_entry_str.set(str(index + 1))

    file_path = os.path.join(root_path, show_image_file_name)
    update_image(file_path)

def update_image(image_path):
    """將 OpenCV 圖片更新到 Tkinter 的 Label"""
    # cv_image =
    # 將 OpenCV 圖片轉換為 PIL 格式
    pil_image = Image.fromarray(cv.imread(image_path, 1))
    tk_image = ImageTk.PhotoImage(pil_image.resize((320, 320)))

    # 更新 Label 的圖片
    image_label.config(image=tk_image)
    image_label.image = tk_image  # 防止被垃圾回收

def set_edit_flag_and_save_button(b: bool = not edit_flag):
    global edit_flag, save_button
    edit_flag = b
    save_button.config(state = tk.NORMAL if edit_flag else tk.DISABLED)


def yes_button_event():
    global model_ans_dict, edit_flag, show_image_file_name
    write_human_dict(
        show_image_file_name,
        model_ans_dict.get(show_image_file_name, "NaN")
    )
    set_edit_flag_and_save_button(True)
    not_tagged_list.remove(show_image_file_name)
    page_down_event()

def enter_event(event):
    ans = human_ans.get().strip()
    if ans == "":
        yes_button.invoke()
        return
    elif len(ans) == 4:
        edit_button.invoke()
        return
    messagebox.showerror("輸入錯誤", "輸入數量有誤！")


def enter_event_without_entry(event):
    if isinstance(event.widget, tk.Entry):
        return  # 如果是輸入框，忽略事件
    enter_event(event)

def edit_button_event():
    global edit_flag, show_image_file_name, human_ans_entry
    user_input = human_ans_entry.get().strip()
    if not user_input:
        messagebox.showerror("輸入錯誤", "輸入不能為空!")
        return

    write_human_dict(
        show_image_file_name,
        user_input
    )
    set_edit_flag_and_save_button(True)
    human_ans_entry.delete(0, tk.END)
    if show_image_file_name in not_tagged_list:
        not_tagged_list.remove(show_image_file_name)
    page_down_event()

def save_button_event():
    global edit_flag
    if edit_flag and messagebox.askyesno("儲存", "要進行存檔嗎?"):
        if not save_human_file():
            return
        set_edit_flag_and_save_button(False)


def exit_event():
    global edit_flag
    if messagebox.askyesno("離開", "確定要離開嗎?"):
        if edit_flag and messagebox.askyesno("儲存", "資料還沒保存，要進行存檔嗎?"):
            if not save_human_file():
                return
            set_edit_flag_and_save_button(False)
        root.quit()

def on_human_ans_input_change(*args):
    # 獲取 Entry 中的文字
    current_text = "".join([c for c in human_ans.get().strip() if c.isdigit()])
    human_ans.set(current_text)
    edit_button.config(
        state =
            tk.NORMAL
            if current_text != "" and len(current_text) == 4
            else
            tk.DISABLED
    )

def on_page_input_change(*args):
    # 獲取 Entry 中的文字
    current_text = "".join([c for c in page_entry_str.get().strip() if c.isdigit()])
    page_entry_str.set(current_text)


def button_invoke_without_entry(event, button):
    # 判斷事件來源是否是輸入框
    if event.widget != root:
        return  # 如果是輸入框，忽略事件
    button.invoke()

def on_key_press(event):
    if event.widget != root:
        return  # 如果是輸入框，忽略事件
    key = event.keysym  # 獲取按鍵名稱
    match key:
        case "d" | "D":
            page_down_button.invoke()
        case "a" | "A":
            page_up_button.invoke()
        case "w" | "W":
            page_return_button.invoke()

def write_human_dict(key: str, value: str):
    global human_ans_dict
    human_ans_dict[key] = value

def check_human_file():
    global human_file_path
    if not os.path.exists(human_file_path):
        with open(human_file_path, "x",encoding = "utf-8"): pass

def save_human_file():
    global human_ans_dict, human_file_path
    try:
        with open(human_file_path, "w",encoding = "utf-8") as f:
            json.dump(human_ans_dict, f, indent = 4, ensure_ascii = False)
        return True
    except:
        messagebox.showerror("檔案錯誤", "人類答案儲存失敗！")
        return False


def focus_event(event):
    # 讓 root 獲取焦點，從而讓 Entry 失焦
    event.widget.focus_set()



if __name__ == "__main__":
    global model_ans_dict, not_tagged_list, human_ans_dict, all_data_list


    if not os.path.exists(model_file_path):
        exit("找不到模型答案！")

    with open(model_file_path, "r",encoding = "utf-8") as f:
        model_ans_dict = json.load(f)

    if not os.path.exists(human_file_path):
        with open(human_file_path, "x",encoding = "utf-8") as f:
            pass

    try :
        with open(human_file_path, "r",encoding = "utf-8") as f:
            human_ans_dict = json.load(f)
    except json.decoder.JSONDecodeError:
        human_ans_dict = {}

    # 過濾掉已經回答的問題
    not_tagged_dict = {
        key: value
        for key, value in model_ans_dict.items()
        if key not in human_ans_dict.keys()
    }
    # 再創建 key list
    not_tagged_list = sorted(
        not_tagged_dict.keys(),
        key=lambda x: int(get_file_name_number(x))
    )
    all_data_list = sorted(
        model_ans_dict.keys(),
        key=lambda x: int(get_file_name_number(x))
    )

    # 創建 tkinter 視窗
    root = tk.Tk()

    root.bind("<Return>", enter_event_without_entry)
    root.bind("<Left>", lambda event: button_invoke_without_entry(event, page_up_button))
    root.bind("<Right>", lambda event: button_invoke_without_entry(event, page_down_button))
    root.bind("<Up>", lambda event: button_invoke_without_entry(event, page_return_button))
    root.bind("<KeyPress>", on_key_press)

    root.bind("<Button-1>", focus_event)

    human_ans = tk.StringVar()
    page_entry_str = tk.StringVar()
    all_data_index = tk.IntVar()
    # progress_bar_str = tk.StringVar()
    progress_bar_percent_str = tk.StringVar()

    human_ans.trace_add("write", on_human_ans_input_change)  # 當變數內容變化時觸發回呼函式
    page_entry_str.trace_add("write", on_page_input_change)

    root.title("人工人智慧檢查")
    root.geometry("800x600")
    root.state('zoomed')

    # 圖片框
    image_label = tk.Label(root)
    image_label.pack(pady=5)

    # model 答案
    ans_label = tk.Label(
        root,
        text="None",
        font=('Arial', 32, 'bold')
    )
    ans_label.pack(pady=10)
    # 輸入框
    human_ans_entry = tk.Entry(
        root,
        width=30,
        font=('Arial', 24),
        textvariable = human_ans
    )
    human_ans_entry.pack(pady=15)
    human_ans_entry.bind("<Return>", enter_event)
    human_ans_entry.bind("<Escape>", lambda event: root.focus_set())

    button_frame = tk.Frame(root, pady=10, padx=10)

    yes_button = tk.Button(
        button_frame,
        text="Yes",
        command=yes_button_event,
        font=('Arial', 24),
    )
    yes_button.pack(side= "left", anchor="center", padx=5, pady=10)

    edit_button = tk.Button(
        button_frame,
        text="Edit",
        command=edit_button_event,
        font=('Arial', 24),
    )
    edit_button.pack(side= "left", anchor="center", padx=5, pady=10)

    save_button = tk.Button(
        button_frame,
        text="Save",
        command=save_button_event,
        font=('Arial', 24),
        state=tk.DISABLED,
    )
    save_button.pack(side= "left", anchor="center", padx=5, pady=10)

    exit_button = tk.Button(
        button_frame,
        text="Exit",
        command=exit_event,
        font=('Arial', 24),
    )
    exit_button.pack(side= "left", anchor="center", padx=5, pady=10)
    button_frame.pack()  # 再放 button_frame



    change_page_frame = tk.Frame(root, pady=10, padx=10)

    page_up_button = tk.Button(change_page_frame, text="<-", command=page_up_event)
    page_up_button.pack(side= "left", anchor="center", padx=5, pady=10)

    page_return_button = tk.Button(
        change_page_frame,
        text="^",
        command = init_page
    )
    page_return_button.pack(side= "left", anchor="center", padx=5, pady=10)

    page_entry = tk.Entry(
        change_page_frame,
        width=10,
        font=('Arial', 24),
        textvariable = page_entry_str
    )
    page_entry.pack(side= "left", anchor="center", padx=5, pady=10)
    page_entry.bind("<Return>", lambda event: page_to_button.invoke())
    page_entry.bind("<Escape>", lambda event: root.focus_set())

    page_to_button = tk.Button(change_page_frame, text="To", command=page_to_event)
    page_to_button.pack(side= "left", anchor="center", padx=5, pady=10)

    page_down_button = tk.Button(change_page_frame, text="->", command=page_down_event)
    page_down_button.pack(side= "left", anchor="center", padx=5, pady=10)

    change_page_frame.pack()  # 再放 button_frame



    all_page_label = tk.Label(
        root,
        text = f"{(all_data_index.get() + 1)}/{len(all_data_list)}",
        font=('Arial', 20),
    )
    all_page_label.pack(anchor="center", pady=10)

    # progress_bar_str.set(f"0% [{' ' * 50}] 0%")
    # progress_bar_label = tk.Label(
    #     root,
    #     textvariable = progress_bar_str,
    #     font=('Arial', 20),
    # )
    # progress_bar_label.pack(anchor="center", pady=10)

    progress_bar_frame = tk.Frame(root, pady=10, padx=10)
    progress_bar_percent_label_1 = tk.Label(
        progress_bar_frame,
        textvariable = progress_bar_percent_str,
        font=('Arial', 20),
    )
    progress_bar_percent_label_1.pack(side= "left", anchor="center", padx=5, pady=0)

    progress_bar = ttk.Progressbar(
        progress_bar_frame,
        orient = "horizontal",
        length = 250,
        mode = "determinate"
    )
    progress_bar.pack(side= "left", anchor="center", padx=5, pady=0)

    progress_bar_percent_label_2 = tk.Label(
        progress_bar_frame,
        textvariable = progress_bar_percent_str,
        font=('Arial', 20),
    )
    progress_bar_percent_label_2.pack(side= "left", anchor="center", padx=5, pady=0)
    progress_bar_frame.pack()
    # progress_bar["value"] = 150

    # progress_bar_label_test_1 = tk.Label(
    #     root,
    #     text = f"0% [{'◼' * 25}] 0%",
    #     font=('Arial', 20),
    # )
    # progress_bar_label_test_1.pack(anchor="center", pady=10)
    # progress_bar_label_test_2 = tk.Label(
    #     root,
    #     text = f"0% [{' ' * 50}] 0%",
    #     font=('Arial', 20),
    # )
    # progress_bar_label_test_2.pack(anchor="center", pady=10)


    init_page()
    root.protocol("WM_DELETE_WINDOW", exit_event)
    # 啟動 tkinter 主迴圈
    root.mainloop()
