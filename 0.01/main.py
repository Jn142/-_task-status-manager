import sys
import os
import webbrowser
from datetime import datetime
from typing import List, Tuple
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QListWidget, QPushButton, QLabel, QTableWidget, QTableWidgetItem,
                             QComboBox, QInputDialog, QMessageBox, QTreeWidget, QTreeWidgetItem,
                             QDateEdit, QMenu, QAction, QListWidgetItem, QDialog, QFormLayout,
                             QFileDialog, QLineEdit, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, QDate, QSize, QRect, QPoint, QTimer
from PyQt5.QtGui import QPalette, QColor, QFont, QBrush, QPainter, QLinearGradient
from db_helper import DBHelper


class GradientBackgroundWidget(QWidget):
    """带渐变背景的自定义部件"""

    def paintEvent(self, event):
        painter = QPainter(self)
        gradient = QLinearGradient(QPoint(0, 0), QPoint(0, self.height()))
        gradient.setColorAt(0, QColor(240, 248, 255))  # 浅蓝
        gradient.setColorAt(1, QColor(255, 255, 255))  # 白色
        painter.fillRect(self.rect(), QBrush(gradient))
        super().paintEvent(event)


class TaskManager(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = DBHelper()
        self.current_board_id = None
        self.current_board_name = ""
        self.init_ui()
        self.set_style()
        # 初始化属性相关下拉框数据
        self.load_property_combo_data()

    def init_ui(self):
        self.setWindowTitle("任务状态管理器")
        self.resize(2000, 900)  # 加宽窗口容纳新功能

        # 菜单栏（不变）
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 5px;
                margin: 5px 5px 0 5px;
            }
            QMenuBar::item {
                background-color: white;
                color: #333;
                padding: 6px 18px;
                margin: 0 3px;
                border-radius: 15px;
                border: 1px solid transparent;
                font-size: 16px;
            }
            QMenuBar::item:hover {
                border: 1px solid #ccc;
                background-color: #f9f9f9;
            }
            QMenuBar::item:selected {
                background-color: #e6f0ff;
                border: 1px solid #b3d1ff;
            }
            QMenu {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 6px;
                padding: 5px 0;
                font-size: 15px;
            }
            QMenu::item {
                padding: 6px 25px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #e6f0ff;
                color: #333;
            }
        """)
        file_menu = menubar.addMenu("文件(F)")
        exit_action = QAction("退出(E)", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 主布局（不变）
        main_widget = GradientBackgroundWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        # 左侧板块面板（不变）
        left_panel = self._create_left_panel()
        main_layout.addWidget(left_panel, 1)

        # 右侧内容面板（新增属性功能+日期全属性查询）
        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel, 3)

        self.setCentralWidget(main_widget)
        self.load_boards()

    def _create_left_panel(self) -> QWidget:
        """左侧板块面板（不变）"""
        panel = QWidget()
        panel.setObjectName("leftPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        title_label = QLabel("<b>任务板块</b>")
        title_label.setObjectName("panelTitle")
        layout.addWidget(title_label)

        self.board_list = QListWidget()
        self.board_list.setObjectName("boardList")
        self.board_list.itemClicked.connect(self.on_board_click)
        self.board_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.board_list.customContextMenuRequested.connect(self.show_board_context_menu)
        self.board_list.setAlternatingRowColors(True)
        layout.addWidget(self.board_list)

        add_btn = QPushButton("+ 新建任务板块")
        add_btn.setObjectName("addButton")
        add_btn.clicked.connect(self.add_board)
        layout.addWidget(add_btn)

        return panel

    def _create_right_panel(self) -> QWidget:
        """右侧内容面板（新增日期全属性查询按钮）"""
        panel = QWidget()
        panel.setObjectName("rightPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # ------------------------------
        # 1. 属性管理区域（显示预设属性+删除按钮）
        # ------------------------------
        prop_manage_layout = QVBoxLayout()
        prop_manage_label = QLabel("<b>属性管理（点击删除自定义属性）</b>")
        prop_manage_label.setObjectName("panelTitle")
        prop_manage_layout.addWidget(prop_manage_label)

        # 属性显示表格（2列：属性名、操作）
        self.prop_table = QTableWidget()
        self.prop_table.setColumnCount(2)
        self.prop_table.setHorizontalHeaderLabels(["属性名称", "操作"])
        self.prop_table.horizontalHeader().setSectionResizeMode(0, 1)
        self.prop_table.horizontalHeader().setSectionResizeMode(1, 0)
        self.prop_table.setColumnWidth(1, 120)
        self.prop_table.verticalHeader().setDefaultSectionSize(50)
        self.prop_table.setAlternatingRowColors(True)
        prop_manage_layout.addWidget(self.prop_table)
        layout.addLayout(prop_manage_layout)

        # ------------------------------
        # 2. 自定义属性提交区域
        # ------------------------------
        custom_prop_layout = QHBoxLayout()
        custom_prop_layout.setSpacing(15)

        self.custom_prop_input = QLineEdit()
        self.custom_prop_input.setObjectName("nameSearchInput")
        self.custom_prop_input.setPlaceholderText("\"输入自定义属性（如\"设计任务\"）...\"")

        self.submit_prop_btn = QPushButton("提交属性")
        self.submit_prop_btn.setObjectName("searchButton")
        self.submit_prop_btn.clicked.connect(self.submit_custom_property)

        # 新增：模式查询按钮
        self.mode_query_btn = QPushButton("查询目录模式任务")
        self.mode_query_btn.setObjectName("searchButton")
        self.mode_query_btn.clicked.connect(self.search_tasks_by_mode)
        self.mode_query_btn.setContextMenuPolicy(Qt.CustomContextMenu)
        self.mode_query_btn.customContextMenuRequested.connect(self.switch_query_mode)

        custom_prop_layout.addWidget(QLabel("自定义属性："))
        custom_prop_layout.addWidget(self.custom_prop_input)
        custom_prop_layout.addWidget(self.submit_prop_btn)
        custom_prop_layout.addWidget(self.mode_query_btn)
        custom_prop_layout.addStretch()
        layout.addLayout(custom_prop_layout)

        # ------------------------------
        # 3. 查询区域（新增：日期+全属性查询按钮）
        # ------------------------------
        search_layout = QVBoxLayout()

        # 3.1 日期+属性筛选组合（新增"日期+全属性查询"按钮）
        combo_search_layout = QHBoxLayout()
        combo_search_layout.setSpacing(15)

        # 年份/月份筛选（原有）
        self.year_combo = QComboBox()
        self.year_combo.setObjectName("searchCombo")
        current_year = datetime.now().year
        self.year_combo.addItems([str(current_year - 1), str(current_year), str(current_year + 1)])
        self.year_combo.setCurrentText(str(current_year))

        self.month_combo = QComboBox()
        self.month_combo.setObjectName("searchCombo")
        self.month_combo.addItems([str(i) for i in range(1, 13)])
        self.month_combo.setCurrentText(str(datetime.now().month))

        # 属性筛选下拉框（原有）
        self.prop_combo = QComboBox()
        self.prop_combo.setObjectName("searchCombo")
        self.prop_combo.setPlaceholderText("选择属性...")

        # 查询按钮（3个：属性查询、日期+属性查询、日期+全属性查询）
        self.prop_only_search_btn = QPushButton("按属性查询所有任务")
        self.prop_only_search_btn.setObjectName("searchButton")
        self.prop_only_search_btn.clicked.connect(self.search_tasks_by_property_only)

        self.prop_date_search_btn = QPushButton("按日期+指定属性查询")
        self.prop_date_search_btn.setObjectName("searchButton")
        self.prop_date_search_btn.clicked.connect(self.search_tasks_by_date_and_property)

        # 新增：日期+全属性查询按钮（查询指定日期下所有属性的任务）
        self.all_prop_date_search_btn = QPushButton("按日期+全属性查询")
        self.all_prop_date_search_btn.setObjectName("searchButton")
        self.all_prop_date_search_btn.clicked.connect(self.search_tasks_by_date_all_property)

        combo_search_layout.addWidget(QLabel("年份："))
        combo_search_layout.addWidget(self.year_combo)
        combo_search_layout.addWidget(QLabel("月份："))
        combo_search_layout.addWidget(self.month_combo)
        combo_search_layout.addWidget(QLabel("属性："))
        combo_search_layout.addWidget(self.prop_combo)
        combo_search_layout.addWidget(self.prop_only_search_btn)
        combo_search_layout.addWidget(self.prop_date_search_btn)
        combo_search_layout.addWidget(self.all_prop_date_search_btn)  # 新增按钮
        combo_search_layout.addStretch()
        search_layout.addLayout(combo_search_layout)

        # 3.2 任务名称检索+排序（原有）
        name_search_layout = QHBoxLayout()
        name_search_layout.setSpacing(15)

        self.task_name_input = QLineEdit()
        self.task_name_input.setObjectName("nameSearchInput")
        self.task_name_input.setPlaceholderText("输入任务名称关键词检索...")

        name_search_btn = QPushButton("名称检索")
        name_search_btn.setObjectName("searchButton")
        name_search_btn.clicked.connect(self.search_tasks_by_name)

        sort_by_name_btn = QPushButton("按任务名称排序（所有）")
        sort_by_name_btn.setObjectName("actionButton")
        sort_by_name_btn.clicked.connect(self.load_all_tasks_order_by_name)

        name_search_layout.addWidget(QLabel("任务名称："))
        name_search_layout.addWidget(self.task_name_input)
        name_search_layout.addWidget(name_search_btn)
        name_search_layout.addWidget(sort_by_name_btn)
        name_search_layout.addStretch()
        search_layout.addLayout(name_search_layout)

        layout.addLayout(search_layout)

        # ------------------------------
        # 4. 时间目录树（原有）
        # ------------------------------
        self.task_tree = QTreeWidget()
        self.task_tree.setObjectName("taskTree")
        self.task_tree.setHeaderLabel("时间目录")
        self.task_tree.itemClicked.connect(self.on_tree_item_click)
        layout.addWidget(self.task_tree)

        # ------------------------------
        # 5. 任务表格（含任务属性列，原有）
        # ------------------------------
        self.task_table = QTableWidget()
        self.task_table.setObjectName("taskTable")
        self.task_table.setColumnCount(12)  # 调整为12列
        self.task_table.setHorizontalHeaderLabels([
            "任务名称", "所属板块", "任务属性", "状态", "状态时间",
            "预计启用时间", "任务目录", "设置目录", "跳转/复制", "操作按钮", "属性ID", "任务ID"
        ])
        # 行高/列宽设置
        self.task_table.verticalHeader().setDefaultSectionSize(70)
        self.task_table.verticalHeader().setMinimumSectionSize(50)
        self.task_table.horizontalHeader().setSectionResizeMode(0, 1)
        self.task_table.horizontalHeader().setSectionResizeMode(1, 1)
        self.task_table.horizontalHeader().setSectionResizeMode(2, 1)
        self.task_table.horizontalHeader().setSectionResizeMode(3, 1)
        self.task_table.horizontalHeader().setSectionResizeMode(4, 1)
        self.task_table.horizontalHeader().setSectionResizeMode(5, 1)
        self.task_table.horizontalHeader().setSectionResizeMode(6, 1)
        self.task_table.horizontalHeader().setSectionResizeMode(7, 0)
        self.task_table.horizontalHeader().setSectionResizeMode(8, 0)
        self.task_table.horizontalHeader().setSectionResizeMode(9, 0)
        # 具体列宽
        self.task_table.setColumnWidth(0, 100)
        self.task_table.setColumnWidth(1, 100)
        self.task_table.setColumnWidth(2, 120)  # 任务属性列
        self.task_table.setColumnWidth(3, 120)
        self.task_table.setColumnWidth(4, 200)
        self.task_table.setColumnWidth(5, 200)
        self.task_table.setColumnWidth(6, 200)
        self.task_table.setColumnWidth(7, 150)
        self.task_table.setColumnWidth(8, 150)
        self.task_table.setColumnWidth(9, 150)  # 操作按钮列
        self.task_table.hideColumn(10)  # 隐藏属性ID列
        self.task_table.hideColumn(11)  # 隐藏任务ID列
        self.task_table.setAlternatingRowColors(True)
        # 任务表格右键菜单（新增更改属性）
        self.task_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.task_table.customContextMenuRequested.connect(self.show_task_context_menu)
        layout.addWidget(self.task_table)

        # ------------------------------
        # 6. 新建任务按钮（原有）
        # ------------------------------
        add_task_btn = QPushButton("+ 新建任务")
        add_task_btn.setObjectName("addButton")
        add_task_btn.clicked.connect(self.add_task)
        layout.addWidget(add_task_btn)

        return panel

    def set_style(self):
        """全局样式（不变）"""
        self.setStyleSheet("""
            /* 全局字体 */
            * {
                font-family: "SimHei", "Microsoft YaHei", sans-serif;
                font-size: 26px;
            }
            /* 面板样式 */
            #leftPanel, #rightPanel {
                background-color: rgba(255, 255, 255, 0.9);
                border-radius: 10px;
                box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12);
                padding: 5px;
            }
            /* 面板标题 */
            #panelTitle {
                color: #2c3e50;
                font-size: 28px;
                padding-bottom: 8px;
                border-bottom: 1px solid #eee;
            }
            /* 列表样式 */
            #boardList {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                font-size: 27px;
            }
            #boardList::item {
                padding: 10px 8px;
                border-radius: 4px;
            }
            #boardList::item:selected {
                background-color: #3498db;
                color: white;
            }
            #boardList::item:hover {
                background-color: #f0f7ff;
            }
            /* 树形目录 */
            #taskTree {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                font-size: 27px;
            }
            #taskTree::item {
                padding: 6px;
                border-radius: 4px;
            }
            #taskTree::item:selected {
                background-color: #3498db;
                color: white;
            }
            #taskTree::item:hover {
                background-color: #f0f7ff;
            }
            #taskTree QHeaderView::section {
                font-size: 27px;
                padding: 8px;
            }
            /* 表格样式（含属性管理表格） */
            #taskTable, #propTable {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 26px;
                gridline-color: #f0f0f0;
            }
            #taskTable QHeaderView::section, #propTable QHeaderView::section {
                background-color: #f5f5f5;
                padding: 10px;
                border: 1px solid #e0e0e0;
                color: #333;
                font-size: 26px;
                font-weight: bold;
            }
            #taskTable::item, #propTable::item {
                padding: 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            #taskTable::item:selected, #propTable::item:selected {
                background-color: #e6f0ff;
                color: #333;
            }
            /* 按钮样式 */
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 26px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1f6dad;
            }
            #searchButton {
                background-color: #2ecc71;
            }
            #searchButton:hover {
                background-color: #27ae60;
            }
            .deleteBtn {
                background-color: #e74c3c;
            }
            .deleteBtn:hover {
                background-color: #c0392b;
            }
            .renameBtn {
                background-color: #f39c12;
            }
            .renameBtn:hover {
                background-color: #e67e22;
            }
            .propDeleteBtn {
                background-color: #e74c3c;
                font-size: 24px;
                padding: 5px 10px;
            }
            /* 下拉框样式 */
            #searchCombo {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 26px;
                background-color: white;
            }
            #searchCombo::drop-down {
                border-radius: 0 6px 6px 0;
            }
            /* 输入框样式 */
            #nameSearchInput {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 26px;
                background-color: white;
            }
            #nameSearchInput::placeholder {
                color: #aaa;
            }
            /* 标签样式 */
            QLabel {
                color: #333;
                font-size: 26px;
            }
            /* 对话框样式 */
            QDialog {
                background-color: white;
                border-radius: 10px;
                font-size: 26px;
            }
            QInputDialog QLabel {
                font-size: 26px;
                color: #333;
            }
            QInputDialog QLineEdit, QInputDialog QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 8px;
                font-size: 26px;
                min-width: 250px;
            }
        """)

    # ------------------------------
    # 新增功能：操作按钮右键切换功能
    # ------------------------------
    def show_operation_menu(self, button):
        """显示操作按钮的右键菜单"""
        menu = QMenu(self)

        update_status_action = QAction("修改状态", menu)
        update_status_action.triggered.connect(
            lambda: self.switch_operation_function(button, "update_status", "修改状态"))

        rename_action = QAction("重命名", menu)
        rename_action.triggered.connect(lambda: self.switch_operation_function(button, "rename", "重命名"))

        delete_action = QAction("删除任务", menu)
        delete_action.triggered.connect(lambda: self.switch_operation_function(button, "delete", "删除任务"))

        menu.addAction(update_status_action)
        menu.addAction(rename_action)
        menu.addAction(delete_action)

        # 在按钮位置显示菜单
        global_pos = button.mapToGlobal(QPoint(0, button.height()))
        menu.exec_(global_pos)

    def switch_operation_function(self, button, function, display_text):
        """切换操作按钮的功能"""
        button.setText(display_text)
        button.setProperty("current_function", function)

        # 根据功能设置按钮颜色
        if function == "update_status":
            button.setStyleSheet("")  # 默认颜色
        elif function == "rename":
            button.setStyleSheet("background-color: #f39c12;")  # 橙色
        elif function == "delete":
            button.setStyleSheet("background-color: #e74c3c;")  # 红色

    def execute_current_operation(self, task_id, task_name):
        """执行当前选定的操作"""
        # 获取当前按钮
        button = self.sender()
        if not button:
            return

        current_function = button.property("current_function")

        if current_function == "update_status":
            self.update_task_status(task_id)
        elif current_function == "rename":
            self.rename_task(task_id, task_name)
        elif current_function == "delete":
            self.delete_task(task_id)

    # ------------------------------
    # 核心功能1：属性管理（原有，不变）
    # ------------------------------
    def load_property_combo_data(self) -> None:
        """加载属性数据到下拉框和属性管理表格"""
        # 1. 清空原有数据
        self.prop_combo.clear()
        self.prop_table.setRowCount(0)

        # 2. 获取所有属性
        properties = self.db.get_all_properties()
        for prop_id, prop_name, is_default in properties:
            # 2.1 填充属性筛选下拉框（格式：属性名（默认/自定义））
            suffix = "(默认)" if is_default == 1 else "(自定义)"
            self.prop_combo.addItem(f"{prop_name} {suffix}", prop_id)

            # 2.2 填充属性管理表格
            row = self.prop_table.rowCount()
            self.prop_table.insertRow(row)
            # 2.2.1 属性名称列（默认属性标红）
            name_item = QTableWidgetItem(prop_name)
            if is_default == 1:
                name_item.setForeground(QColor(231, 76, 60))  # 红色标注默认属性
            self.prop_table.setItem(row, 0, name_item)
            # 2.2.2 操作列（默认属性无删除按钮）
            if is_default == 0:
                delete_btn = QPushButton("删除")
                delete_btn.setObjectName("propDeleteBtn")
                delete_btn.clicked.connect(lambda checked, pid=prop_id: self.delete_property(pid))
                self.prop_table.setCellWidget(row, 1, delete_btn)
            else:
                self.prop_table.setItem(row, 1, QTableWidgetItem("—"))  # 默认属性不可删除

    def submit_custom_property(self) -> None:
        """提交自定义属性"""
        prop_name = self.custom_prop_input.text().strip()
        if not prop_name:
            QMessageBox.warning(self, "提示", "属性名称不能为空！")
            return

        # 调用数据库方法新增属性
        if self.db.add_custom_property(prop_name):
            QMessageBox.information(self, "成功", f"自定义属性「{prop_name}」已添加！")
            self.custom_prop_input.clear()
            self.load_property_combo_data()  # 刷新属性列表
        else:
            QMessageBox.warning(self, "失败", f"属性「{prop_name}」已存在！")

    def delete_property(self, prop_id: int) -> None:
        """删除属性（触发数据库逻辑）"""
        task_count, success = self.db.delete_property(prop_id)
        if not success:
            QMessageBox.warning(self, "提示", "默认属性不可删除！")
            return

        # 提示删除结果
        msg = f"属性删除成功！\n共有 {task_count} 个任务的属性已改为「未知」"
        QMessageBox.information(self, "成功", msg)

        # 刷新属性列表和任务表格
        self.load_property_combo_data()
        if self.current_board_id and self.task_tree.currentItem():
            data = self.task_tree.currentItem().data(0, Qt.UserRole)
            if data and data[0] == "month":
                self.load_tasks_by_month(data[1], data[2])
        else:
            self.search_tasks_by_time_status()

    # ------------------------------
    # 核心功能2：任务属性修改（原有，不变）
    # ------------------------------
    def show_task_context_menu(self, position) -> None:
        """任务表格右键菜单（新增"更改属性"和"切换模式"）"""
        # 获取当前选中行
        selected_items = self.task_table.selectedItems()
        if not selected_items:
            return
        current_row = selected_items[0].row()

        # 获取当前任务的属性ID、任务ID和模式
        prop_id = int(self.task_table.item(current_row, 10).text())
        task_id = int(self.task_table.item(current_row, 11).text())
        link_mode_item = self.task_table.item(current_row, 9)
        link_mode = int(link_mode_item.text()) if link_mode_item and link_mode_item.text().isdigit() else 0

        # 创建右键菜单
        context_menu = QMenu(self.task_table)
        # 新增：更改属性选项
        change_prop_action = QAction("更改任务属性", context_menu)
        change_prop_action.triggered.connect(lambda: self.change_task_property(task_id, prop_id))
        context_menu.addAction(change_prop_action)

        # 新增：切换模式选项
        change_mode_action = QAction("切换任务模式", context_menu)
        change_mode_action.triggered.connect(lambda: self.switch_task_mode(task_id, link_mode))
        context_menu.addAction(change_mode_action)

        # 显示菜单
        global_pos = self.task_table.mapToGlobal(position)
        context_menu.exec_(global_pos)

    def change_task_property(self, task_id: int, current_prop_id: int) -> None:
        """更改任务属性（弹窗选择新属性）"""
        # 1. 获取所有属性，生成选项列表
        properties = self.db.get_all_properties()
        prop_options = []
        prop_ids = []
        current_index = 0
        for idx, (prop_id, prop_name, is_default) in enumerate(properties):
            suffix = "(默认)" if is_default == 1 else "(自定义)"
            prop_options.append(f"{prop_name} {suffix}")
            prop_ids.append(prop_id)
            # 定位当前属性的索引
            if prop_id == current_prop_id:
                current_index = idx

        # 2. 弹窗选择新属性
        new_prop_text, ok = QInputDialog.getItem(
            self,
            "更改任务属性",
            "选择新属性：",
            prop_options,
            current_index,
            False
        )
        if not ok:
            return

        # 3. 获取新属性ID并更新
        new_prop_index = prop_options.index(new_prop_text)
        new_prop_id = prop_ids[new_prop_index]
        self.db.update_task_property(task_id, new_prop_id)

        # 4. 刷新任务表格
        QMessageBox.information(self, "成功", "任务属性已更新！")
        if self.current_board_id and self.task_tree.currentItem():
            data = self.task_tree.currentItem().data(0, Qt.UserRole)
            if data and data[0] == "month":
                self.load_tasks_by_month(data[1], data[2])
        else:
            self.search_tasks_by_time_status()

    # ------------------------------
    # 新增功能1：模式查询功能
    # ------------------------------
    def search_tasks_by_mode(self) -> None:
        """按模式查询任务"""
        if self.mode_query_btn.text() == "查询目录模式任务":
            mode = 0
            mode_name = "目录模式"
        else:
            mode = 1
            mode_name = "链接模式"

        results = self.db.get_tasks_by_link_mode(mode)
        if not results:
            QMessageBox.information(self, "结果", f"未找到{mode_name}任务")
            self.task_table.setRowCount(0)
            return

        self.show_search_results(results)
        QMessageBox.information(self, "查询结果", f"找到 {len(results)} 个{mode_name}任务")

    def switch_query_mode(self) -> None:
        """切换查询模式"""
        if self.mode_query_btn.text() == "查询目录模式任务":
            self.mode_query_btn.setText("查询链接模式任务")
            self.search_tasks_by_mode()  # 立即查询
        else:
            self.mode_query_btn.setText("查询目录模式任务")
            self.search_tasks_by_mode()  # 立即查询

    # ------------------------------
    # 新增功能2：任务模式切换
    # ------------------------------
    def switch_task_mode(self, task_id: int, current_mode: int) -> None:
        """切换单个任务的模式"""
        new_mode = 1 if current_mode == 0 else 0
        mode_name = "链接模式" if new_mode == 1 else "目录模式"

        confirm = QMessageBox.question(
            self,
            "确认切换",
            f"确定将任务切换到{mode_name}？",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            self.db.update_task_link_mode(task_id, new_mode)
            # 刷新显示
            if self.current_board_id and self.task_tree.currentItem():
                data = self.task_tree.currentItem().data(0, Qt.UserRole)
                if data and data[0] == "month":
                    self.load_tasks_by_month(data[1], data[2])
            QMessageBox.information(self, "成功", f"任务已切换到{mode_name}")

    # ------------------------------
    # 新增功能3：链接相关操作
    # ------------------------------
    def set_task_link(self, task_id: int) -> None:
        """设置任务链接"""
        current_link = self.db.get_task_link_url(task_id)
        new_link, ok = QInputDialog.getText(
            self,
            "设置链接",
            "请输入任务链接：",
            text=current_link or ""
        )
        if ok and new_link.strip():
            self.db.update_task_link_url(task_id, new_link.strip())
            # 刷新显示
            if self.current_board_id and self.task_tree.currentItem():
                data = self.task_tree.currentItem().data(0, Qt.UserRole)
                if data and data[0] == "month":
                    self.load_tasks_by_month(data[1], data[2])
            QMessageBox.information(self, "成功", "链接已更新")

    def copy_task_link(self, task_id: int) -> None:
        """复制任务链接到剪贴板"""
        link = self.db.get_task_link_url(task_id)
        if link:
            QApplication.clipboard().setText(link)
            QMessageBox.information(self, "成功", "链接已复制到剪贴板")
        else:
            QMessageBox.warning(self, "提示", "该任务未设置链接")

    def jump_to_link(self, task_id: int) -> None:
        """跳转到任务链接"""
        link = self.db.get_task_link_url(task_id)
        if link:
            try:
                webbrowser.open(link)
            except Exception as e:
                QMessageBox.warning(self, "错误", f"无法打开链接: {str(e)}")
        else:
            QMessageBox.warning(self, "提示", "该任务未设置链接")

    # ------------------------------
    # 核心功能3：查询功能（新增日期全属性查询）
    # ------------------------------
    def search_tasks_by_property_only(self) -> None:
        """按属性查询所有任务（不限制日期）"""
        if self.prop_combo.currentIndex() == -1:
            QMessageBox.warning(self, "提示", "请先选择属性！")
            return

        # 获取选中的属性ID
        prop_id = self.prop_combo.currentData()
        prop_name = self.db.get_property_name_by_id(prop_id)

        # 查询任务
        results = self.db.get_tasks_by_property(prop_id)
        if not results:
            QMessageBox.information(self, "结果", f"未找到属性为「{prop_name}」的任务")
            self.task_table.setRowCount(0)
            return

        # 显示结果
        self.show_search_results(results)
        QMessageBox.information(self, "结果", f"找到 {len(results)} 个属性为「{prop_name}」的任务")

    def search_tasks_by_date_and_property(self) -> None:
        """按日期（年/月）+ 指定属性查询"""
        if self.prop_combo.currentIndex() == -1:
            QMessageBox.warning(self, "提示", "请先选择属性！")
            return

        # 获取筛选条件
        year = int(self.year_combo.currentText())
        month = int(self.month_combo.currentText())
        prop_id = self.prop_combo.currentData()
        prop_name = self.db.get_property_name_by_id(prop_id)

        # 查询任务
        results = self.db.get_tasks_by_date_and_property(year, month, prop_id)
        if not results:
            msg = f"未找到 {year}年{month}月 属性为「{prop_name}」的任务"
            QMessageBox.information(self, "结果", msg)
            self.task_table.setRowCount(0)
            return

        # 显示结果
        self.show_search_results(results)
        msg = f"找到 {year}年{month}月 共 {len(results)} 个属性为「{prop_name}」的任务"
        QMessageBox.information(self, "结果", msg)

    def search_tasks_by_date_all_property(self) -> None:
        """新增：按日期（年/月）+ 全属性查询（查询指定日期下所有属性的任务）"""
        # 获取筛选条件（仅年份和月份，不限制属性）
        year = int(self.year_combo.currentText())
        month = int(self.month_combo.currentText())

        # 调用数据库方法查询（复用原有按时间查询逻辑，不传递属性ID即查所有属性）
        results = self.db.get_tasks_by_time_status(year=year, month=month, status=None)
        if not results:
            msg = f"未找到 {year}年{month}月 的任何任务"
            QMessageBox.information(self, "结果", msg)
            self.task_table.setRowCount(0)
            return

        # 统计各属性的任务数量（增强用户体验）
        prop_count = {}
        for task in results:
            prop_name = task[11]  # 结果元组中第11位是属性名称
            prop_count[prop_name] = prop_count.get(prop_name, 0) + 1

        # 生成统计信息
        count_msg = f"{year}年{month}月 任务统计：\n"
        for prop, count in prop_count.items():
            count_msg += f"- {prop}：{count}个\n"
        count_msg += f"总计：{len(results)}个任务"

        # 显示结果
        self.show_search_results(results)
        QMessageBox.information(self, "结果", count_msg)

    def search_tasks_by_name(self) -> None:
        """按任务名称模糊检索（原有，不变）"""
        task_name = self.task_name_input.text().strip()
        if not task_name:
            QMessageBox.warning(self, "提示", "请输入任务名称关键词！")
            return

        results = self.db.search_tasks_by_name(task_name)
        if not results:
            QMessageBox.information(self, "结果", f"未找到包含「{task_name}」的任务")
            self.task_table.setRowCount(0)
            return

        self.show_search_results(results)
        QMessageBox.information(self, "结果", f"找到{len(results)}条包含「{task_name}」的任务")

    # ------------------------------
    # 核心功能4：修复删除任务闪退（关键修改）
    # ------------------------------
    def safe_refresh_after_delete(self):
        """安全刷新界面（删除任务后调用）"""
        try:
            # 清空表格避免数据不一致
            self.task_table.setRowCount(0)

            # 重新加载时间目录树
            if self.current_board_id:
                self.load_time_tree()

            # 尝试重新加载当前选中的月份
            current_item = self.task_tree.currentItem()
            if current_item:
                data = current_item.data(0, Qt.UserRole)
                if (data and isinstance(data, tuple) and len(data) >= 3
                        and data[0] == "month"):
                    # 使用QTimer确保UI更新完成后再加载数据
                    QTimer.singleShot(50, lambda: self.load_tasks_by_month(data[1], data[2]))

        except Exception as e:
            print(f"刷新异常: {e}")
            # 异常时的降级处理
            self.task_table.setRowCount(0)

    def delete_task(self, task_id: int) -> None:
        """删除任务（修复空指针访问，避免闪退）"""
        confirm = QMessageBox.question(
            self,
            "确认删除",
            "确定删除该任务吗？删除后不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            self.db.delete_task(task_id)
            QMessageBox.information(self, "成功", "任务已删除！")

            # 使用安全刷新方法
            self.safe_refresh_after_delete()

    # ------------------------------
    # 原有功能（适配修复与新增功能，不变）
    # ------------------------------
    def show_board_context_menu(self, position) -> None:
        current_item = self.board_list.itemAt(position)
        if not current_item:
            return

        context_menu = QMenu(self.board_list)
        rename_action = QAction("重命名板块", context_menu)
        rename_action.triggered.connect(lambda: self.rename_board(current_item))
        delete_action = QAction("删除板块", context_menu)
        delete_action.triggered.connect(lambda: self.delete_board(current_item))

        context_menu.addAction(rename_action)
        context_menu.addAction(delete_action)
        global_pos = self.board_list.mapToGlobal(position)
        context_menu.exec_(global_pos)

    def rename_board(self, item) -> None:
        board_id = item.data(Qt.UserRole)
        old_name = item.text()
        new_name, ok = QInputDialog.getText(
            self,
            "重命名板块",
            f"当前板块：{old_name}\n请输入新名称：",
            text=old_name
        )
        if not ok:
            return
        new_name = new_name.strip()
        if new_name == old_name:
            QMessageBox.information(self, "提示", "新名称与原名称一致，无需修改")
            return
        if not new_name:
            QMessageBox.warning(self, "提示", "板块名称不能为空！")
            return

        if self.db.update_board_name(board_id, new_name):
            item.setText(new_name)
            self.current_board_name = new_name
            QMessageBox.information(self, "成功", f"板块已重命名为「{new_name}」")
            if self.current_board_id == board_id and self.task_tree.currentItem():
                data = self.task_tree.currentItem().data(0, Qt.UserRole)
                if data and data[0] == "month":
                    self.load_tasks_by_month(data[1], data[2])
        else:
            QMessageBox.warning(self, "失败", "新板块名称已存在！")

    def delete_board(self, item) -> None:
        board_id = item.data(Qt.UserRole)
        board_name = item.text()
        confirm = QMessageBox.question(
            self,
            "确认删除",
            f"确定删除「{board_name}」？\n关联的所有任务将一并删除！",
            QMessageBox.Yes | QMessageBox.No
        )

        if confirm == QMessageBox.Yes:
            self.db.delete_board(board_id)
            self.load_boards()
            self.task_tree.clear()
            self.task_table.setRowCount(0)

    def load_boards(self) -> None:
        self.board_list.clear()
        boards = self.db.get_all_boards()
        for board_id, name in boards:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, board_id)
            self.board_list.addItem(item)

    def add_board(self) -> None:
        name, ok = QInputDialog.getText(self, "新建板块", "请输入板块名称：")
        if ok and name.strip():
            if self.db.add_board(name.strip()):
                QMessageBox.information(self, "成功", f"板块「{name}」创建成功")
                self.load_boards()
            else:
                QMessageBox.warning(self, "失败", "该板块名称已存在！")

    def on_board_click(self, item) -> None:
        self.current_board_id = item.data(Qt.UserRole)
        self.current_board_name = item.text()
        self.load_time_tree()

    def load_time_tree(self) -> None:
        self.task_tree.clear()
        if not self.current_board_id:
            return

        tasks = self.db.get_tasks_by_board(self.current_board_id)
        existing_year_month = set((task[1], task[2]) for task in tasks)
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        existing_year_month.add((current_year, current_month))

        year_items = {}
        sorted_year_month = sorted(existing_year_month, key=lambda x: (-x[0], -x[1]))

        for year, month in sorted_year_month:
            if year not in year_items:
                year_item = QTreeWidgetItem([str(year)])
                year_item.setData(0, Qt.UserRole, ("year", year))
                self.task_tree.addTopLevelItem(year_item)
                year_items[year] = year_item
            month_item = QTreeWidgetItem([f"{month}月"])
            month_item.setData(0, Qt.UserRole, ("month", year, month))
            year_items[year].addChild(month_item)

        if current_year in year_items:
            year_items[current_year].setExpanded(True)

    def on_tree_item_click(self, item) -> None:
        data = item.data(0, Qt.UserRole)
        if not data:
            return
        if data[0] == "month":
            year, month = data[1], data[2]
            self.load_tasks_by_month(year, month)

    def load_tasks_by_month(self, year: int, month: int) -> None:
        """加载指定月份任务（含属性列和模式列）"""
        if not self.current_board_id:
            return
        tasks = self.db.get_tasks_by_board(self.current_board_id)
        filtered = [t for t in tasks if t[1] == year and t[2] == month]

        self.task_table.setRowCount(len(filtered))
        for row, task in enumerate(filtered):
            # 任务元组：(id, year, month, name, status, status_time, expected_time, task_dir, property_id, property_name, link_mode, link_url)
            task_id, y, m, name, status, status_time, expected_time, task_dir, prop_id, prop_name, link_mode, link_url = task

            # 0-6列：基础信息（新增任务属性列）
            self.task_table.setItem(row, 0, QTableWidgetItem(name))
            self.task_table.setItem(row, 1, QTableWidgetItem(self.current_board_name))
            self.task_table.setItem(row, 2, QTableWidgetItem(prop_name))  # 任务属性列
            self.task_table.setItem(row, 3, QTableWidgetItem(status))
            self.task_table.setItem(row, 4, QTableWidgetItem(status_time.split('.')[0]))
            self.task_table.setItem(row, 5, QTableWidgetItem(expected_time or "-"))

            # 第6列：根据模式显示目录或链接
            if link_mode == 0:  # 目录模式
                self.task_table.setItem(row, 6, QTableWidgetItem(task_dir or "未设置"))
            else:  # 链接模式
                self.task_table.setItem(row, 6, QTableWidgetItem(link_url or "未设置"))

            # 第7列：设置按钮（根据模式显示不同文本和功能）
            if link_mode == 0:  # 目录模式
                set_btn = QPushButton("设置目录")
                set_btn.setObjectName("actionButton")
                set_btn.clicked.connect(lambda checked, tid=task_id: self.set_task_dir(tid))
                # 右键菜单用于切换模式
                set_btn.setContextMenuPolicy(Qt.CustomContextMenu)
                set_btn.customContextMenuRequested.connect(lambda pos, tid=task_id: self.switch_task_mode(tid, 0))
            else:  # 链接模式
                set_btn = QPushButton("设置链接")
                set_btn.setObjectName("actionButton")
                set_btn.clicked.connect(lambda checked, tid=task_id: self.set_task_link(tid))
                # 右键菜单用于切换模式
                set_btn.setContextMenuPolicy(Qt.CustomContextMenu)
                set_btn.customContextMenuRequested.connect(lambda pos, tid=task_id: self.switch_task_mode(tid, 1))

            self.task_table.setCellWidget(row, 7, set_btn)

            # 第8列：操作按钮（根据模式显示不同文本和功能）
            if link_mode == 0:  # 目录模式
                action_btn = QPushButton("跳转目录")
                action_btn.setObjectName("actionButton")
                action_btn.clicked.connect(lambda checked, tid=task_id: self.jump_to_dir(tid))
            else:  # 链接模式
                action_btn = QPushButton("复制链接")
                action_btn.setObjectName("actionButton")
                action_btn.clicked.connect(lambda checked, tid=task_id: self.copy_task_link(tid))
                # 右键菜单用于跳转链接
                action_btn.setContextMenuPolicy(Qt.CustomContextMenu)
                action_btn.customContextMenuRequested.connect(lambda pos, tid=task_id: self.jump_to_link(tid))

            self.task_table.setCellWidget(row, 8, action_btn)

            # 第9列：操作按钮（通过右键切换功能）
            op_btn = QPushButton("修改状态")
            op_btn.setObjectName("actionButton")
            op_btn.setProperty("current_function", "update_status")  # 存储当前功能
            op_btn.setProperty("task_id", task_id)  # 存储任务ID
            op_btn.setProperty("task_name", name)  # 存储任务名称

            # 左键点击执行当前功能
            op_btn.clicked.connect(lambda checked, tid=task_id, tname=name: self.execute_current_operation(tid, tname))

            # 右键点击切换功能
            op_btn.setContextMenuPolicy(Qt.CustomContextMenu)
            op_btn.customContextMenuRequested.connect(lambda pos, btn=op_btn: self.show_operation_menu(btn))

            self.task_table.setCellWidget(row, 9, op_btn)

            # 隐藏列：属性ID、任务ID
            self.task_table.setItem(row, 10, QTableWidgetItem(str(prop_id)))
            self.task_table.setItem(row, 11, QTableWidgetItem(str(task_id)))

    def add_task(self) -> None:
        """新建任务（含属性选择和模式选择）"""
        if not self.current_board_id:
            QMessageBox.warning(self, "提示", "请先选择任务板块！")
            return

        # 任务名称
        name, ok = QInputDialog.getText(self, "新建任务", "任务名称：")
        if not ok or not name.strip():
            return
        name = name.strip()

        # 任务状态
        statuses = ["待启用", "初开启", "已完成"]
        status, ok = QInputDialog.getItem(self, "选择状态", "任务状态：", statuses, 0, False)
        if not ok:
            return

        # 任务属性（原有）
        properties = self.db.get_all_properties()
        prop_options = [f"{p[1]} {'(默认)' if p[2] == 1 else '(自定义)'}" for p in properties]
        prop_ids = [p[0] for p in properties]
        prop_text, ok = QInputDialog.getItem(
            self,
            "选择任务属性",
            "任务属性：",
            prop_options,
            2,  # 默认选"未知"（索引2）
            False
        )
        if not ok:
            return
        prop_id = prop_ids[prop_options.index(prop_text)]

        # 新增：任务模式选择
        modes = ["目录模式", "链接模式"]
        mode_choice, ok = QInputDialog.getItem(
            self,
            "选择任务模式",
            "请选择任务关联方式：",
            modes,
            0,  # 默认选目录模式
            False
        )
        if not ok:
            return

        link_mode = 0 if mode_choice == "目录模式" else 1
        link_url = None
        task_dir = None

        # 根据模式进行不同设置
        if link_mode == 0:  # 目录模式
            # 原有目录设置逻辑
            if QMessageBox.question(self, "设置任务目录", "是否为任务设置目录路径？",
                                    QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
                task_dir = QFileDialog.getExistingDirectory(self, "选择任务目录")
        else:  # 链接模式
            # 新增链接设置逻辑
            link_url, ok = QInputDialog.getText(
                self,
                "设置链接",
                "请输入任务链接：",
                text=""
            )
            if not ok or not link_url.strip():
                return
            link_url = link_url.strip()

        # 预计启用时间
        expected_time = None
        if status == "待启用":
            date_dialog = QDialog(self)
            date_dialog.setWindowTitle("设置预计启用时间")
            date_dialog.resize(350, 150)
            layout = QFormLayout(date_dialog)

            date_edit = QDateEdit(QDate.currentDate())
            date_edit.setDisplayFormat("yyyy-MM-dd")
            date_edit.setCalendarPopup(True)
            date_edit.setMinimumHeight(30)
            layout.addRow("选择日期：", date_edit)

            btn_layout = QHBoxLayout()
            ok_btn = QPushButton("确认")
            cancel_btn = QPushButton("取消")
            ok_btn.clicked.connect(date_dialog.accept)
            cancel_btn.clicked.connect(date_dialog.reject)
            btn_layout.addWidget(ok_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addRow(btn_layout)

            if date_dialog.exec_() == QDialog.Accepted:
                expected_time = date_edit.date().toString("yyyy-MM-dd")

        # 保存任务（新增link_mode和link_url参数）
        self.db.add_task(
            board_id=self.current_board_id,
            name=name,
            status=status,
            property_id=prop_id,
            expected_time=expected_time,
            task_dir=task_dir,
            link_mode=link_mode,
            link_url=link_url
        )
        self.load_time_tree()
        QMessageBox.information(self, "成功", "任务创建成功！")

    def rename_task(self, task_id: int, old_name: str) -> None:
        new_name, ok = QInputDialog.getText(
            self,
            "重命名任务",
            f"当前任务：{old_name}\n请输入新名称：",
            text=old_name
        )
        if not ok:
            return
        new_name = new_name.strip()
        if new_name == old_name:
            QMessageBox.information(self, "提示", "新名称与原名称一致，无需修改")
            return
        if not new_name:
            QMessageBox.warning(self, "提示", "任务名称不能为空！")
            return

        self.db.update_task_name(task_id, new_name)
        QMessageBox.information(self, "成功", f"任务已重命名为「{new_name}」")

        if self.current_board_id and self.task_tree.currentItem():
            data = self.task_tree.currentItem().data(0, Qt.UserRole)
            if data and data[0] == "month":
                self.load_tasks_by_month(data[1], data[2])
        else:
            self.search_tasks_by_time_status()

    def set_task_dir(self, task_id: int) -> None:
        new_dir = QFileDialog.getExistingDirectory(self, "选择新的任务目录")
        if not new_dir:
            return

        self.db.update_task_dir(task_id, new_dir)
        QMessageBox.information(self, "成功", "任务目录已更新！")

        if self.current_board_id and self.task_tree.currentItem():
            data = self.task_tree.currentItem().data(0, Qt.UserRole)
            if data and data[0] == "month":
                self.load_tasks_by_month(data[1], data[2])
        else:
            self.search_tasks_by_time_status()

    def jump_to_dir(self, task_id: int) -> None:
        tasks = self.db.get_tasks_by_time_status()
        task_dir = None
        for task in tasks:
            if task[0] == task_id:
                task_dir = task[9]  # 第9位是task_dir
                break

        if not task_dir:
            QMessageBox.warning(self, "提示", "该任务未设置目录！")
            return

        if not os.path.exists(task_dir):
            QMessageBox.warning(self, "提示", f"目录不存在：{task_dir}")
            return

        os.startfile(task_dir)

    def update_task_status(self, task_id: int) -> None:
        statuses = ["待启用", "初开启", "已完成"]
        new_status, ok = QInputDialog.getItem(self, "修改状态", "新状态：", statuses, 0, False)
        if ok:
            self.db.update_task_status(task_id, new_status)
            if self.current_board_id and self.task_tree.currentItem():
                data = self.task_tree.currentItem().data(0, Qt.UserRole)
                if data and data[0] == "month":
                    self.load_tasks_by_month(data[1], data[2])
            else:
                self.search_tasks_by_time_status()
            QMessageBox.information(self, "成功", "状态已更新！")

    def load_all_tasks_order_by_name(self) -> None:
        tasks = self.db.get_all_tasks_order_by_name()
        if not tasks:
            QMessageBox.information(self, "提示", "暂无任务数据！")
            self.task_table.setRowCount(0)
            return

        self.show_search_results(tasks)
        QMessageBox.information(self, "完成", f"已按任务名称排序，共{len(tasks)}条任务")

    def search_tasks_by_time_status(self) -> None:
        year = int(self.year_combo.currentText())
        month = int(self.month_combo.currentText())
        status = self.status_combo.currentText() if hasattr(self, 'status_combo') else None
        status = status if status != "全部" else None

        results = self.db.get_tasks_by_time_status(year, month, status)
        self.show_search_results(results)

    def show_search_results(self, results: List[Tuple]) -> None:
        """显示检索/排序结果（含任务属性列和模式列）"""
        self.task_table.setRowCount(len(results))
        for row, res in enumerate(results):
            # 结果元组：(id, name, board_name, year, month, status, status_time, expected_time, board_id, task_dir, property_id, property_name, link_mode, link_url)
            (task_id, name, board_name, year, month, status, status_time,
             expected_time, board_id, task_dir, prop_id, prop_name, link_mode, link_url) = res

            # 0-6列：基础信息
            self.task_table.setItem(row, 0, QTableWidgetItem(name))
            self.task_table.setItem(row, 1, QTableWidgetItem(board_name))
            self.task_table.setItem(row, 2, QTableWidgetItem(prop_name))  # 任务属性列
            self.task_table.setItem(row, 3, QTableWidgetItem(status))
            self.task_table.setItem(row, 4, QTableWidgetItem(status_time.split('.')[0]))
            self.task_table.setItem(row, 5, QTableWidgetItem(expected_time or "-"))

            # 第6列：根据模式显示目录或链接
            if link_mode == 0:  # 目录模式
                self.task_table.setItem(row, 6, QTableWidgetItem(task_dir or "未设置"))
            else:  # 链接模式
                self.task_table.setItem(row, 6, QTableWidgetItem(link_url or "未设置"))

            # 第7列：设置按钮（根据模式显示不同文本和功能）
            if link_mode == 0:  # 目录模式
                set_btn = QPushButton("设置目录")
                set_btn.setObjectName("actionButton")
                set_btn.clicked.connect(lambda checked, tid=task_id: self.set_task_dir(tid))
                # 右键菜单用于切换模式
                set_btn.setContextMenuPolicy(Qt.CustomContextMenu)
                set_btn.customContextMenuRequested.connect(lambda pos, tid=task_id: self.switch_task_mode(tid, 0))
            else:  # 链接模式
                set_btn = QPushButton("设置链接")
                set_btn.setObjectName("actionButton")
                set_btn.clicked.connect(lambda checked, tid=task_id: self.set_task_link(tid))
                # 右键菜单用于切换模式
                set_btn.setContextMenuPolicy(Qt.CustomContextMenu)
                set_btn.customContextMenuRequested.connect(lambda pos, tid=task_id: self.switch_task_mode(tid, 1))

            self.task_table.setCellWidget(row, 7, set_btn)

            # 第8列：操作按钮（根据模式显示不同文本和功能）
            if link_mode == 0:  # 目录模式
                action_btn = QPushButton("跳转目录")
                action_btn.setObjectName("actionButton")
                action_btn.clicked.connect(lambda checked, tid=task_id: self.jump_to_dir(tid))
            else:  # 链接模式
                action_btn = QPushButton("复制链接")
                action_btn.setObjectName("actionButton")
                action_btn.clicked.connect(lambda checked, tid=task_id: self.copy_task_link(tid))
                # 右键菜单用于跳转链接
                action_btn.setContextMenuPolicy(Qt.CustomContextMenu)
                action_btn.customContextMenuRequested.connect(lambda pos, tid=task_id: self.jump_to_link(tid))

            self.task_table.setCellWidget(row, 8, action_btn)

            # 第9列：操作按钮（通过右键切换功能）
            op_btn = QPushButton("修改状态")
            op_btn.setObjectName("actionButton")
            op_btn.setProperty("current_function", "update_status")  # 存储当前功能
            op_btn.setProperty("task_id", task_id)  # 存储任务ID
            op_btn.setProperty("task_name", name)  # 存储任务名称

            # 左键点击执行当前功能
            op_btn.clicked.connect(lambda checked, tid=task_id, tname=name: self.execute_current_operation(tid, tname))

            # 右键点击切换功能
            op_btn.setContextMenuPolicy(Qt.CustomContextMenu)
            op_btn.customContextMenuRequested.connect(lambda pos, btn=op_btn: self.show_operation_menu(btn))

            self.task_table.setCellWidget(row, 9, op_btn)

            # 隐藏列：属性ID、任务ID
            self.task_table.setItem(row, 10, QTableWidgetItem(str(prop_id)))
            self.task_table.setItem(row, 11, QTableWidgetItem(str(task_id)))

    def closeEvent(self, event) -> None:
        self.db.close()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont("SimHei")
    app.setFont(font)
    window = TaskManager()
    window.show()
    sys.exit(app.exec_())