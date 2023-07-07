import os, sys, math, requests, socket, threading, pypdf, re, time, shutil, psutil
from bs4 import BeautifulSoup
from PyQt6.QtCore import Qt, QThreadPool, QRunnable, pyqtSlot, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QComboBox, QHBoxLayout
from PyQt6.QtWidgets import QCheckBox, QFileDialog, QMessageBox, QGridLayout, QTextEdit, QProgressBar, QDialog
from PyQt6.QtGui import QGuiApplication, QPalette, QColor
from concurrent.futures import ThreadPoolExecutor, as_completed

base_url = "https://www.survivorlibrary.com"
website_url = base_url + "/library-download.html"  # Replace with the actual website URL
agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/91.0.4472.124 Safari/537.36"
headers = {"User-Agent": agent}

# progress, increment, and total_files for the progress_bar. retriever for fetch_bar
# downloaded and remaining for how many bytes have downloaded and how many bytes are left
progress, increment, total_files, retriever, downloaded, remaining = (0, 0, 0, 0, 0, 0)
dark_mode, last_time = (True, time.time())
stop_requested, close_windows, internet_disconnected = (False, False, False)
start_time = time.time()
# count_files and count_track to keep track of when code started and finished downloading a certain category.
count_files, count_track = ({}, {})
disconnect_lock = threading.Lock()
output_lock = threading.Lock()

class DownloadWorker(QRunnable):
    def __init__(self, url, filename, folder, chunk_size, output_window):
        super(DownloadWorker, self).__init__()
        self.url = url
        self.filename = filename
        self.folder = folder
        self.chunk_size = chunk_size
        self.output_window = output_window

    def run(self): 
        try:
            cat_folder = os.path.basename(self.folder)
            if cat_folder not in count_track:
                count_track[cat_folder] = 0
                if not close_windows:
                    output_lock.acquire()
                    self.output_window.append_text(f"Started downloading {cat_folder} category...")
                    output_lock.release()
        
            response = requests.get(self.url, headers=headers, stream = True)
            if response.status_code == 200:
                file_path = os.path.join(self.folder, self.filename)
                
                with open(file_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if stop_requested:
                            if not close_windows:
                                self.output_window.append_text(f"Failed to download {self.filename}.")
                            file.close()
                            os.remove(file_path)
                            self.output_window.time_label.setText("0 seconds remaining")
                            return
                        if chunk:
                            file.write(chunk)
                            elapsed_time = time.time() - start_time
                            global last_time, downloaded, remaining
                            downloaded += len(chunk)
                            remaining -= len(chunk)
                            if remaining <= 0:
                                remaining = 0
                            if not close_windows:
                                if (time.time() - last_time) >= 0.5:
                                    time_left = self.measure_download(remaining , downloaded, elapsed_time)
                                    self.output_window.time_label.setText(time_left)
       
                global progress, increment, total_files
                increment += 1
                progress = int((increment / total_files) * 100)
                self.output_window.set_progress.emit(progress)
                
                # If internet is disconnected, files that are currently downloading (not to confuse with files that are on 
                # queue, waiting to be downloaded) will be corrupted. Check for those corrupted files and delete.
                try:
                    with open(file_path, 'rb') as file:
                        reader = pypdf.PdfReader(file)
                        self.output_window.append_text(f"Downloaded {self.filename} successfully.")
                except Exception:
                    os.remove(file_path)
                    if not close_windows:
                        self.output_window.append_text(f"Failed to download {self.filename}.")
                
                count_track[cat_folder] += 1
            
            else:
                if not close_windows:
                    self.output_window.append_text(f"Failed to download {self.filename}.")
                count_track[cat_folder] += 1
            
            if count_track[cat_folder] == count_files[cat_folder]:
                if not close_windows:
                    self.output_window.append_text(f"Finished downloading {cat_folder} category.")
        
        # If internet disconnected, show user the proper error message
        except (requests.exceptions.RequestException, socket.gaierror):
            global internet_disconnected
            disconnect_lock.acquire()
            if not internet_disconnected:
                self.output_window.internet_disconnected.emit()
                internet_disconnected = True
            disconnect_lock.release()
    
    # Find the remaining time to finish download
    def measure_download(self, download_size , chunk_value, elapsed):
        down_speed = (chunk_value * 8) / elapsed
        seconds = (download_size * 8) / down_speed

        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        
        global last_time ; last_time = time.time() 
        time_parts = []

        if int(hours) > 0:
            time_parts.append(f"{int(hours)} {'hour' if int(hours) == 1 else 'hours'}")
        if int(minutes) > 0:
            time_parts.append(f"{int(minutes)} {'minute' if int(minutes) == 1 else 'minutes'}")
        if int(seconds) > 0:
            time_parts.append(f"{int(seconds)} {'second' if int(seconds) == 1 else 'seconds'} remaining")

        return ', '.join(time_parts)

class OutputWindow(QWidget):
    set_progress = pyqtSignal(int)
    fetch_progress = pyqtSignal(int)
    internet_disconnected = pyqtSignal() 
    
    def __init__(self, threadpool):
        super(OutputWindow, self).__init__()
        self.setWindowTitle("Output")
        self.layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setMinimumSize(800, 600) 
        self.layout.addWidget(self.text_edit)
        
        title_label = QLabel("Retrieving Download Links and Checking for Corrupted Files Progress:")
        self.layout.addWidget(title_label)
        
        self.fetch_bar = QProgressBar(self)
        self.layout.addWidget(self.fetch_bar)
        self.fetch_bar.setAlignment(Qt.AlignmentFlag.AlignCenter) 
        
        progress_layout = QHBoxLayout()
        self.title_label = QLabel("Download Progress:")
        self.time_label = QLabel(self)
        
        # Set Download Progress and estimated time at two ends of the window
        progress_layout.addWidget(self.title_label, alignment=Qt.AlignmentFlag.AlignLeft)
        progress_layout.addWidget(self.time_label, alignment=Qt.AlignmentFlag.AlignRight)
        self.layout.addLayout(progress_layout)
        
        self.progress_bar = QProgressBar(self)
        self.layout.addWidget(self.progress_bar)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.cancel_button = QPushButton("Cancel Download")
        self.cancel_button.clicked.connect(self.force_stop)
        
        self.layout.addWidget(self.cancel_button)
        self.setLayout(self.layout)
        self.threadpool = threadpool
        
        self.fetch_progress.connect(self.fetch_bar.setValue)
        self.set_progress.connect(self.progress_bar.setValue)
        self.internet_disconnected.connect(self.show_internet_disconnected_error) 

    def append_text(self, text):
        self.text_edit.append(text)
        self.text_edit.ensureCursorVisible()        # Auto scroll to the bottom new download logs are appended
        
    def show_internet_disconnected_error(self):
        QMessageBox.warning(self, "Error", "Internet disconnected. The downloading process has been stopped.")
        
    def force_stop(self):
        self.threadpool.clear()
        global stop_requested
        stop_requested = True
        self.close()
    
    # Setup for light mode of the output window
    def out_light_mode(self):
        
        # Setup the main color palette for light mode
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        self.setPalette(palette)
        
        # Buttons and progress bars not affected by palette change. Need to tweak manually.
        # Clear up the style sheet set up by dark mode
        self.cancel_button.setStyleSheet("")
        self.progress_bar.setStyleSheet("")
        self.fetch_bar.setStyleSheet("")
        self.text_edit.setStyleSheet("")
        
        # Fix some colors to fit the light theme
        self.text_edit.setStyleSheet("QTextEdit" "{" "border : 1px black;" "}")
        self.progress_bar.setStyleSheet("QProgressBar" "{" "color : black" "}")
        self.fetch_bar.setStyleSheet("QProgressBar" "{" "color : black" "}")
        
    def out_dark_mode(self):
        # Setup the main color palette for light mode
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(33, 33, 33))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        self.setPalette(palette) 

        # Dark theme for buttons, progress bar, and QTextEdit
        button_stylesheet = "background-color: #212121; color: white; border: 0.5px solid white; padding: 2px;"
        self.cancel_button.setStyleSheet(button_stylesheet)
        
        # rgba(0, 0, 0, 0) to make the progress bar background transparent
        bar_style = "background-color : rgba(0, 0, 0, 0); border : 1px solid white; color : white"
        self.progress_bar.setStyleSheet(bar_style)
        self.progress_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fetch_bar.setStyleSheet(bar_style)
        self.fetch_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.text_edit.setStyleSheet(bar_style)
        
class FeaturesWindow(QDialog):
    def __init__(self):
        super(FeaturesWindow, self).__init__()
        self.setWindowTitle("Quirks and Features")

        layout = QVBoxLayout(self)
        self.notes_label = QLabel()
        notes_text = """
        <style> h3 {font-weight: normal;} </style>
        <h3>Couple of Quirks and Features</h3>
        <ul>
            <li style="margin-bottom: 7px;">While holding the Shift key, if you select two topics, all categories between 
            those two topics will be selected.</li>
            <li style="margin-bottom: 7px;">Let's say you are downloading files using the program, and suddenly your PC  
            crashes or a power outage <br>occurs. When you run the program next time and select the topics you were 
            downloading, you can enable </br><br>'Check for Corrupted Files' and the program will delete the corrupted files 
            and download fresh copies. More </br><br>about this topic is discussed later.</br></li>
            <li style="margin-bottom: 7px;">The application skips files you already have. So, you can download your favorite
            topics, run the program<br> six months later, and update your folder with new files that have been added to the
            Survivor Library</br><br> in the last six months,</br></li>
        </ul>
        <h3>Details about Corrupted File Checking</h3>
        <ul>
            <li style="margin-bottom: 7px;">After downloading a pdf from Survivor Library, the program checks if the file is
            corrupted or not. If the file is <br>corrupted, it is deleted. Currently, there are the only 16 corrupted files 
            in out of over 14,000 files in the</br><br> Survivor Library.</br></li>
            <li style="margin-bottom: 7px;">If the checkbox 'Check for Corrupted Files' is enabled, the program will delete
            the corrupted files on your PC<br> in your selected categories and download fresh copies. Now let's consider
            some scenarios.</br></li>
            <ul>
                <li style="margin-bottom: 7px;">If you are downloading certain categories for the first time, it doesn't 
                matter whether you enable or<br> disable it because there are no files to check.</br></li>
                <li style="margin-bottom: 7px;">You have downloaded from 20 categories a year ago. Now, you want to check
                whether any new files<br> were added. If you used this application to download those files a year ago, you
                don't need to check</br><br> for corrupted files because after downloading each file, the application 
                automatically checks for it.</br><br> However, even if you enable it, it's not a big deal. It will take 2-3 
                minutes if you have a hard drive,</br><br> and much faster if you have SSD.</li>
                
                <li style="margin-bottom: 7px;">Now, if you have the entire Survivor Library downloaded and want to update 
                your offline copy a year <br>later, then again, if you used this application to download those files a year 
                ago, you don't need to </br><br>check for corrupted files. However, if you do check all the files, it will
                take some time, especially if the </br><br>data is stored on a hard drive. From my testing, to check about 
                12,000 files (close to 200 GB), it takes</br><br> about 35 minutes on a hard drive. I didn't test it on SSD, 
                but I expect the speed to be much faster.</br></li>
                
                <li style="margin-bottom: 7px;">So, the bottom line is, unless this application or Windows crashes, you 
                really don't need to enable<br> the 'Check for Corrupted Files' option.</br></li>
            </ul>
        </ul>

        """
        self.notes_label.setText(notes_text)
        self.notes_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.notes_label)
        self.setLayout(layout)
        
        
    def feat_dark_mode(self):  
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(33, 33, 33))
        self.setPalette(palette)
        self.notes_label.setStyleSheet("color: white")
    
    def feat_light_mode(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        self.setPalette(palette)
        self.notes_label.setStyleSheet("color: black")
    
class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Survivor Library Downloader")
        
        # Check for active internet connection before starting the program
        try:
            requests.get(website_url, headers=headers)
        except (requests.exceptions.RequestException, socket.gaierror):
            QMessageBox.warning(self, "Error",
                "An active internet connection is required to run the program.",)
            return

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.layout = QVBoxLayout(self.central_widget)

        self.location_label = QLabel("Download Location:")
        self.layout.addWidget(self.location_label)

        self.location_button = QPushButton("Choose Location")
        self.location_button.clicked.connect(self.choose_location)
        self.layout.addWidget(self.location_button)
        
        side_layout = QHBoxLayout()
        
        self.mode_combobox = QComboBox()
        self.mode_combobox.addItem("Light Mode")
        self.mode_combobox.addItem("Dark Mode")
        self.mode_combobox.currentIndexChanged.connect(self.change_mode)
        
        self.features_button = QPushButton("Quirks and Features")
        self.features_button.clicked.connect(self.open_features)
        self.features_window = None
        
        side_layout.addWidget(self.mode_combobox)
        side_layout.addWidget(self.features_button)
        self.layout.addLayout(side_layout)
        
        self.rename_checkbox = QCheckBox("Rename Files (When checked, files will be named like 'Accounting Systems 1911.pdf'" 
                                         " instead of the default 'accounting_systems_1911.pdf')")
        self.layout.addWidget(self.rename_checkbox)
        
        self.corrupt_checkbox = QCheckBox("Check for Corrupted Files")
        self.layout.addWidget(self.corrupt_checkbox)
        
        self.category_label = QLabel("Select Categories:")
        self.layout.addWidget(self.category_label)
        
        # Add all the categories from the Survivor Library to the main window
        self.category_layout = QGridLayout()
        self.layout.addLayout(self.category_layout)
        self.populate_category_combobox()
        
        self.shift_pressed = False
        self.last_clicked_checkbox = None

        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(lambda: self.toggle_rows(Qt.CheckState.Checked))
        self.category_layout.addWidget(self.select_all_button, 0, 0)

        self.unselect_all_button = QPushButton("Unselect All")
        self.unselect_all_button.clicked.connect(self.unselect_all)
        self.category_layout.addWidget(self.unselect_all_button, 0, 1)

        self.start_button = QPushButton("Start Download")
        self.start_button.clicked.connect(lambda: self.start_download(link_mapping))
        self.layout.addWidget(self.start_button)
        
        self.output_window = None
        self.output_window_button = QPushButton("Output Window")
        self.output_window_button.clicked.connect(self.open_output_window)
        self.layout.addWidget(self.output_window_button)
        self.change_mode(0)

        self.threadpool = QThreadPool() 
          
    def open_features(self):    
        if self.features_window is None:
            self.features_window =  FeaturesWindow()
        if dark_mode:
            self.features_window.feat_dark_mode()
        self.features_window.show()
        
    # Helper function to switch between light and dark mode
    def change_mode(self, index):
        global dark_mode
        if index == 0: 
            self.set_light_mode()
            if self.output_window != None:
                self.output_window.out_light_mode()
            if self.features_window != None:
                self.features_window.feat_light_mode()
            dark_mode = False
                
        elif index == 1:
            self.set_dark_mode()
            if self.output_window != None:
                self.output_window.out_dark_mode()
            if self.features_window != None:
                self.features_window.feat_dark_mode()
            dark_mode = True
    
    def set_style(self, button_stylesheet):
        self.location_button.setStyleSheet(button_stylesheet)
        self.start_button.setStyleSheet(button_stylesheet)
        self.output_window_button.setStyleSheet(button_stylesheet)
        self.select_all_button.setStyleSheet(button_stylesheet)
        self.unselect_all_button.setStyleSheet(button_stylesheet)
        self.mode_combobox.setStyleSheet(button_stylesheet)
        self.features_button.setStyleSheet(button_stylesheet)

    def set_light_mode(self):
        self.set_style("")
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        self.setPalette(palette)
        
    def set_dark_mode(self):  
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(33, 33, 33))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        self.setPalette(palette)
        
        button_stylesheet = "background-color: #212121; color: white; border: 0.5px solid white; padding: 2px;"
        self.set_style(button_stylesheet)

    # Select all the the topics in each row
    def toggle_rows(self, state):
        for checkbox in self.checkboxes:
            checkbox.setChecked(state == Qt.CheckState.Checked)
            
    def open_output_window(self):
        if self.output_window is None:
            self.output_window = OutputWindow(self.threadpool)
        if dark_mode:
            self.output_window.out_dark_mode()
        else:
            self.output_window.out_light_mode()
        self.output_window.show()
        
    def unselect_all(self):
        for checkbox in self.checkboxes:
            checkbox.setChecked(False)

    def populate_category_combobox(self):
        response = requests.get(website_url, headers=headers)
        html_content = response.text
        soup = BeautifulSoup(html_content, "html.parser")
        table = soup.find("table")
        link_mapping = {}
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            for cell in cells:
                link = cell.find("a")
                if link:
                    category = link.text
                    href = link["href"]
                    link_mapping[category] = href
                        
        # Organize categories in alphabetical order
        sorted_keys = sorted(link_mapping.keys())
        num_columns = 5
        num_topics = len(link_mapping)
        num_rows = math.ceil(num_topics / num_columns)

        self.checkboxes = []
        for i, category in enumerate(sorted_keys):
            checkbox = QCheckBox(category)
            checkbox.clicked.connect(self.checkbox_clicked)
            self.checkboxes.append(checkbox)
            row = i % num_rows + 2
            col = i // num_rows
            self.category_layout.addWidget(checkbox, row, col)
        return link_mapping

    # While holding shift, if two categories are selected, all categories between them will be selected too.
    # last_clicked allows to select groups of topics in non-contiguous manner.
    def checkbox_clicked(self):
        if QApplication.keyboardModifiers() == Qt.KeyboardModifier.ShiftModifier:
            if self.last_clicked_checkbox is not None:
                start_index = self.checkboxes.index(self.last_clicked_checkbox)
                end_index = self.checkboxes.index(self.sender())

                if start_index < end_index:
                    for i in range(start_index + 1, end_index):
                        self.checkboxes[i].setCheckState(Qt.CheckState.Checked)
                else:
                    for i in range(end_index + 1, start_index):
                        self.checkboxes[i].setCheckState(Qt.CheckState.Checked)
                self.last_clicked_checkbox = None
            else:
                self.last_clicked_checkbox = self.sender()

    def choose_location(self):
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Download Location",
            options=QFileDialog.Option.ShowDirsOnly,
        )
        if folder_path:
            self.location_button.setText(folder_path)
        else:
            self.location_button.setText("Choose Location")
    
    # Convert "894 kb", "34 mb" to bytes to compute chunk size
    def convert_to_bytes(self, size_str):
        units = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3}
        
        size_parts = size_str.split()
        if len(size_parts) != 2:
            raise ValueError("Invalid size format: " + size_str)
        
        size_value, size_unit = float(size_parts[0]), size_parts[1].upper()
        if size_unit not in units:
            raise ValueError("Invalid size unit: " + size_unit)
        
        bytes_size = size_value * units[size_unit]
        return int(bytes_size)
    
    def check_empty_map(self, hash_map):
        for value in hash_map.values():
            if value:  # Value is not empty (non-empty hash map)
                return False
        return True  # All values are empty hash maps

    def start_download(self, link_mapping):
        # While a download is already running, prohibits user from starting a new one
        if self.threadpool.activeThreadCount() > 0:
            QMessageBox.warning(self, "Wait", "Please wait for the current downloads to finish or cancel the current the "
                                "current downloads before starting a new download.")
            return
        
        global progress, increment, total_files, count_files, count_track, retriever, stop_requested, downloaded
        progress, increment, total_files, retriever, downloaded = (0, 0, 0, 0, 0)
        chunk_size = sys.maxsize
        stop_requested = False
        file_size = []
        count_files, count_track = ({}, {})
        destination = self.location_button.text()
        selected_categories = [
            checkbox.text() for checkbox in self.checkboxes if checkbox.isChecked()
        ]
        rename = self.rename_checkbox.isChecked()
        check_corrupt = self.corrupt_checkbox.isChecked()
        
        if not selected_categories:
            QMessageBox.warning(self, "Error", "Please select at least one category.")
            return

        if destination == "Choose Location":
            QMessageBox.warning(self, "Error", "Please select a valid destination folder.")
            return
        
        # Store all links to all books that needs to be downloaded
        book_map_all = {}
        cat_length = len(selected_categories)
        
        # When a download process starts, open output window in the proper mode
        self.output_window = OutputWindow(self.threadpool)
        if dark_mode:
            self.output_window.out_dark_mode()
        else:
            self.output_window.out_light_mode()
        self.output_window.show() 
        
        def download_books(category):
            folder_path = os.path.join(destination, category)
            exist_path = os.path.exists(folder_path)

            # Extract book download links from the webpage
            try:
                subject_url = base_url + link_mapping[category]
                response = requests.get(subject_url, headers=headers)
                html_content = response.text
                soup = BeautifulSoup(html_content, "html.parser")
            except requests.exceptions.RequestException:
                self.output_window.append_text("Internet disconnected. The downloading process has been stopped.")
                return

            rows = soup.find("tbody").find_all("tr")
            book_map = {}
            pattern = r'(\d+)([a-z]+)'

            for row in rows:
                if close_windows or stop_requested:
                    return
                columns = row.find_all("td")
                
                # 'Sliderules and Abacus' category has rows that has no columns. So, the column length check.
                # 'Books for Boys and Girls', 'Law', 'Teaching - Civics' has an empty third column. That's why >=
                # 'Radio 73 Magazine' category has empty rows but two columns. So, the find("a") not None check
                if len(columns) >= 2 and columns[1].find("a") is not None:
                    book_title = columns[0].text.strip() + ".pdf"
                    down_link = columns[1].find("a")["href"]
                    
                    # 'Astronomy' has file size like "14mb" unlike the default format "14 mb"
                    if columns[1].text.split()[-2] == "PDF":
                        match = re.match(pattern, columns[1].text.split()[-1])
                        if match:
                            filesize = match.group(1) + " " + match.group(2)
                    else:
                        filesize = columns[1].text.split()[-2] + " " + columns[1].text.split()[-1]
                
                    alternate = os.path.basename(down_link)
                    check_path = os.path.join(folder_path, book_title)
                    check_alter_path = os.path.join(folder_path, alternate)
                    
                    if check_corrupt:
                        if exist_path:
                            if os.path.exists(check_path):
                                try:
                                    # Check for corrupted files to delete and redownload them
                                    with open(check_path, "rb") as file:
                                        reader = pypdf.PdfReader(file)
                                except Exception:
                                    os.remove(check_path)

                            # Check for both default and renamed files
                            if os.path.exists(check_alter_path):
                                try:
                                    with open(check_alter_path, "rb") as file:
                                        reader = pypdf.PdfReader(file)
                                except Exception:
                                    os.remove(check_alter_path)

                            if not (os.path.exists(check_path) or os.path.exists(check_alter_path)):
                                if rename:
                                    book_map[book_title] = down_link
                                else:
                                    book_map[alternate] = down_link
                                file_size.append(filesize)
                        else:
                            if rename:
                                book_map[book_title] = down_link
                            else:
                                book_map[alternate] = down_link
                            file_size.append(filesize)
                    else:
                        if not (os.path.exists(check_path) or os.path.exists(check_alter_path)):
                            if rename:
                                book_map[book_title] = down_link
                            else:
                                book_map[alternate] = down_link
                            file_size.append(filesize)
            
            if len(book_map) == 0:
                self.output_window.append_text(f"You already have all files in the {category} category.")
                
            else:       
                book_map_all[category] = book_map
                count_files[category] = len(book_map)
                global total_files, retriever
                total_files += len(book_map)
        
        # Run multiple iterations of the for loop in parallel
        executor = ThreadPoolExecutor()
        futures = []

        for category in selected_categories:
            futures.append(executor.submit(download_books, category))

        # Wait for all tasks to complete
        for future in as_completed(futures):
            # If 'Cancel' button is clicked, stop executing the code immediately.
            if close_windows or stop_requested:
                executor.shutdown(wait=False)
                break
            future.result()
            retriever += 1
            self.output_window.fetch_progress.emit(int((retriever / cat_length) * 100))
            QApplication.processEvents()
        
        executor.shutdown()
        
        # If all files in the catgories selected are already on PC, show 100% in progress bar
        if not (close_windows or stop_requested):
            if self.check_empty_map(book_map_all):
                self.output_window.fetch_progress.emit(100)
                self.output_window.set_progress.emit(100)
                QApplication.processEvents()
            
            else:
                # Set the minimum file size to the chunk size
                file_size_bytes = []
                for size_str in file_size:
                    bytes_size = self.convert_to_bytes(size_str)
                    file_size_bytes.append(bytes_size)
                    if bytes_size < chunk_size:
                        chunk_size = bytes_size
                
                # Cut the chunk size by half for faster response when clicking Cancel.
                chunk_size = int(chunk_size / 2)
                global start_time, remaining
                remaining = sum(file_size_bytes)
                total, used, free = shutil.disk_usage(destination)
                if remaining > free:
                    QMessageBox.warning(self, "Error", "Not enough disk space available to download all the files.")
                    return
                start_time = time.time()
                
                for category in book_map_all:
                    folder_path = os.path.join(destination, category)
                    os.makedirs(folder_path, exist_ok=True)
                    
                    for book_name, book_url in book_map_all[category].items():
                        worker = DownloadWorker(base_url + book_url, book_name, folder_path, chunk_size, self.output_window)
                        self.threadpool.start(worker)
    
    # Open the main window in center of the screen             
    def center_window(self):
        frame_gm = self.frameGeometry()
        screen = QGuiApplication.primaryScreen()
        center_point = screen.availableGeometry().center()
        frame_gm.moveCenter(center_point)
        self.move(frame_gm.topLeft())

    def showEvent(self, event):
        super().showEvent(event)
        self.center_window()
    
    # Closing both main and output window will have same effect as clicking the 'Cancel' button
    def closeEvent(self, event):
        self.threadpool.clear()
        global close_windows, stop_requested
        close_windows, stop_requested = (True, True)
        self.close()
        super().closeEvent(event)
        
app = QApplication(sys.argv)
main_window = MainWindow()
link_mapping = main_window.populate_category_combobox()
main_window.show()
sys.exit(app.exec())