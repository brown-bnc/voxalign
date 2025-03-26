import numpy as np
import shutil
import subprocess
import os
import pydicom
np.set_printoptions(suppress=True)
from pathlib import Path
import sys
from voxalign.utils import check_external_tools, convert_signs_to_letters
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QTextEdit, QVBoxLayout, QHBoxLayout, QFileDialog, QMessageBox, QLabel, QLineEdit, QCheckBox
)
from PyQt5.QtGui import QIntValidator
from PyQt5.QtCore import Qt
from functools import partial


# Global variables to store selected paths and MNI coordinates
output_folder = ""
T1_dicom = ""
MNI_coords=[]

def compose_fsl_annot_text(colorlist,voxidx,coord):
    # write out annotations file that FSL loads in to show crosshair(s) at selected coordinates
    annotations_txt = f"X Point colour={colorlist[voxidx]} lineWidth=4 honourZLimits=True zmin={coord[0]-2} zmax={coord[0]+2} x={coord[1]} y={coord[2]} \
                        \nY Point colour={colorlist[voxidx]} lineWidth=4 honourZLimits=True zmin={coord[1]-2} zmax={coord[1]+2} x={coord[0]} y={coord[2]} \
                        \nZ Point colour={colorlist[voxidx]} lineWidth=4 honourZLimits=True zmin={coord[2]-2} zmax={coord[2]+2} x={coord[0]} y={coord[1]}\n"
    
    return annotations_txt
    
class HoverButton(QPushButton):
    def __init__(self, text, num1_input, num2_input, num3_input, parent=None):
        super().__init__(text, parent)
        self.num1_input = num1_input
        self.num2_input = num2_input
        self.num3_input = num3_input

    def enterEvent(self, event):
        """Update the tooltip only when the button is hovered over."""
        num1 = self.num1_input.text() if self.num1_input.text() else "999"
        num2 = self.num2_input.text() if self.num2_input.text() else "999"
        num3 = self.num3_input.text() if self.num3_input.text() else "999"

        fsl_command = f'atlasquery -a "Harvard-Oxford Subcortical Structural Atlas" -c {num1},{num2},{num3}'
        subcort_result = subprocess.run(fsl_command, shell=True, capture_output=True, text=True)
        fsl_command = f'atlasquery -a "Harvard-Oxford Cortical Structural Atlas" -c {num1},{num2},{num3}'
        cort_result = subprocess.run(fsl_command, shell=True, capture_output=True, text=True)
   
        tooltip_text = f"{subcort_result.stdout.split('<br>')[-1]}\n{cort_result.stdout.split('<br>')[-1]}"
        self.setToolTip(tooltip_text)  # Dynamically update tooltip

        super().enterEvent(event)  # Call parent class method

class MNILookupApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

        self.nonlin_path=None

    def initUI(self):
        self.setWindowTitle("Spectroscopy Voxel Position MNI Lookup Configuration")
        self.setGeometry(100, 100, 600, 400)
        self.layout = QVBoxLayout()

        # Output folder selection
        self.output_button = QPushButton("Create Output Folder", self)
        self.output_button.clicked.connect(self.select_output_folder)
        self.layout.addWidget(self.output_button)

        self.output_label = QTextEdit(self)
        self.output_label.setReadOnly(True)
        self.layout.addWidget(self.output_label)
        self.layout.addSpacing(20)

        # T1 DICOM selection
        self.T1_button = QPushButton("Select T1 DICOM", self)
        self.T1_button.clicked.connect(self.select_T1_dicom)
        self.layout.addWidget(self.T1_button)

        self.T1_label = QTextEdit(self)
        self.T1_label.setReadOnly(True)
        self.layout.addWidget(self.T1_label)
        self.layout.addSpacing(20)

        # Option to load output folder from previous MNI registration for this participant
        self.prerun_nonlin_button = QPushButton("Use existing MNI registration", self)
        self.prerun_nonlin_button.setToolTip("Select an output folder generated from a previous run of this mni-lookup tool. Can be from a different scan session, as long as it is the same participant.")
        self.prerun_nonlin_button.clicked.connect(self.on_prerun_button_clicked)
        self.layout.addWidget(self.prerun_nonlin_button)
        self.layout.addSpacing(20)

        # Instruction label
        self.label = QLabel("Enter MNI coordinate(s):", self)
        self.layout.addWidget(self.label)
        
        # Container for input fields (stores rows dynamically)
        self.input_container = QVBoxLayout()
        self.layout.addLayout(self.input_container)

        # List to keep track of input row references
        self.rows = []
        self.add_row()        
        
        # Button to add new rows
        self.add_button = QPushButton("Add another MNI coordinate", self)
        self.add_button.clicked.connect(self.add_row)
        self.layout.addWidget(self.add_button)
        self.layout.addSpacing(20)

        self.checkbox = QCheckBox("Use fast (less accurate) registration to MNI space", self)
        self.checkbox.stateChanged.connect(self.checkbox_changed)  # Connect state change
        self.layout.addWidget(self.checkbox)
        self.layout.addSpacing(20)

        # Calculate voxel position button
        self.run_button = QPushButton("Calculate voxel position", self)
        self.run_button.clicked.connect(lambda: (self.validate_MNI_input(), self.run_voxalign_MNI_lookup()))
        self.layout.addWidget(self.run_button)

        self.setLayout(self.layout)

    def on_prerun_button_clicked(self):
        """Calls both select_nonlinear_reg_folder and toggle_checkbox when the button is clicked."""
        self.select_nonlinear_reg_folder()
        if self.nonlin_path is not None:
            self.hide_nonlin_checkbox()

    def hide_nonlin_checkbox(self):
        """Replaces checkbox with a label when button is clicked."""
        # Remove the checkbox
        self.layout.removeWidget(self.checkbox)
        self.checkbox.deleteLater()
        self.checkbox = None  # Avoid accidental access

        # Disable the button after clicking (optional)
        self.prerun_nonlin_button.setEnabled(False)
        self.prerun_nonlin_button.setText("Using pre-run nonlinear MNI registration")
        
    def add_row(self):
        """Adds a new row of three input boxes with a delete button."""
        row_layout = QHBoxLayout()  # Horizontal layout for the new row

        # Input fields with integer validation
        num1_input = QLineEdit(self)
        num1_input.setPlaceholderText("X")
        num1_input.setValidator(QIntValidator())  # Accepts only integers
        num1_input.setAlignment(Qt.AlignCenter)
        num1_input.setFixedSize(40, 25)  

        num2_input = QLineEdit(self)
        num2_input.setPlaceholderText("Y")
        num2_input.setValidator(QIntValidator())
        num2_input.setFixedSize(40, 25)  
        num2_input.setAlignment(Qt.AlignCenter)

        num3_input = QLineEdit(self)
        num3_input.setPlaceholderText("Z")
        num3_input.setValidator(QIntValidator())
        num3_input.setFixedSize(40, 25)  
        num3_input.setAlignment(Qt.AlignCenter)

        # Button to look up atlas region
        atlas_button = HoverButton("🧠", num1_input, num2_input, num3_input)
        atlas_button.setFixedSize(50, 50)
        atlas_button.setStyleSheet("border : none") 

        # Button to remove the row
        delete_button = QPushButton("❌", self)
        delete_button.setFixedSize(50, 50)
        delete_button.setStyleSheet("border : none") 
        delete_button.setToolTip("Delete row")
        delete_button.clicked.connect(partial(self.remove_row, row_layout, num1_input, num2_input, num3_input, atlas_button, delete_button))

        # Add widgets to the row layout
        row_layout.addWidget(num1_input)
        row_layout.addWidget(num2_input)
        row_layout.addWidget(num3_input)
        row_layout.addWidget(atlas_button)
        row_layout.addWidget(delete_button)

        # Add the row layout to the vertical container
        self.input_container.addLayout(row_layout)

        # Store row reference in the list
        self.rows.append((num1_input, num2_input, num3_input, atlas_button,delete_button,row_layout))

    def remove_row(self, row_layout, num1_input, num2_input, num3_input, atlas_button, delete_button):
        """Removes a row from the layout and deletes widgets properly."""

        # Safely delete all widgets in the row
        num1_input.deleteLater()
        num2_input.deleteLater()
        num3_input.deleteLater()
        atlas_button.deleteLater()
        delete_button.deleteLater()  # Ensure the delete button itself is removed

        # Remove the row layout itself
        row_layout.deleteLater()

        # Remove row from the tracking list
        self.rows = [row for row in self.rows if row[-1] is not row_layout]

        # If all rows are deleted, reset `self.rows`
        if not self.rows:
            self.rows = []  # Ensures empty list instead of None

    def validate_MNI_input(self):
        """Validate the input from the three number fields."""
        global MNI_coords
        MNI_coords = []
        for num1_input, num2_input, num3_input, _, _, _ in self.rows:

            try:
                # Convert the inputs to integers
                num1 = int(num1_input.text())
                num2 = int(num2_input.text())
                num3 = int(num3_input.text())
                MNI_coords.append([num1, num2, num3])
            except ValueError:
                # Handle invalid input
                QMessageBox.critical(self, "Error", "Please enter valid integers in all fields.")
                return
            
    def checkbox_changed(self):
        # Handles the checkbox state change
        if self.checkbox.isChecked():            
            QMessageBox.information(self, "Checkbox Unchecked", "The quick nonlinear registration to MNI space takes about 2 minutes")
        else:
            QMessageBox.information(self, "Checkbox Checked", "The slower, more accurate nonlinear registration to MNI space takes about 4 minutes")

    def select_output_folder(self):
        """Opens a dialog to select an empty output folder. Stops if the user cancels."""
        folder_path = None

        while True:
            folder_path = QFileDialog.getExistingDirectory(self, "Select Output Folder")

            if not folder_path:  # User clicked Cancel, stop reopening
                self.output_label.setText("No folder selected")
                return  

            folder_path = Path(folder_path)  # Convert to Path object

            # Check if the folder is empty
            if any(folder_path.iterdir()):  # If the folder contains files/subfolders
                response = QMessageBox.warning(
                    self, "Folder Not Empty",
                    "The selected folder is not empty. Please select an empty folder.",
                    QMessageBox.Retry | QMessageBox.Cancel
                )

                if response == QMessageBox.Cancel:
                    return  # Exit the function completely if Cancel is clicked
                else:
                    continue  # Retry selecting a new folder
            else:
                # Folder is empty, set it as the output folder
                self.output_folder = folder_path
                self.output_label.setText(str(self.output_folder))
                return  # Exit the loop

    def select_T1_dicom(self):
        global T1_dicom
        T1_dicom, _ = QFileDialog.getOpenFileName(self, "Select T1 DICOM", "", "DICOM files (*.dcm)")
        if T1_dicom:
            self.T1_label.setText(T1_dicom)
        else:
            self.T1_label.setText("No file selected")

    def select_nonlinear_reg_folder(self):
        """Opens a dialog to select a pre-run nonlinear registration folder. Stops if the user cancels."""
        nonlin_folder_path = None

        while True:
            nonlin_folder_path = QFileDialog.getExistingDirectory(self, "Select Folder with Pre-run Nonlinear MNI Registration")

            if not nonlin_folder_path:
                return
            
            nonlin_folder_path = Path(nonlin_folder_path)  # Convert to Path object

            self.required_files = ["T1.nii", "T1_ss.nii.gz", "T1toMNI_warp.nii.gz","croppedT1.nii.gz","T1toMNInonlin.nii.gz"]

            # Check if the folder contains the required files
            req_files_exist = [os.path.exists(os.path.join(nonlin_folder_path,file)) for file in self.required_files]

            if not all(req_files_exist):  # If the folder contains files/subfolders
                response = QMessageBox.warning(
                    self, "Missing required files",
                    "Folder does not contain all required files. Please try again or run nonlinear alignment now.",
                    QMessageBox.Retry | QMessageBox.Cancel
                )

                if response == QMessageBox.Cancel:
                    return  # Exit the function completely if Cancel is clicked
                else:
                    continue  # Retry selecting a new folder
            else:
                self.nonlin_path = nonlin_folder_path
                return  # Exit the loop
    

    def run_voxalign_MNI_lookup(self):
        self.run_button.setDisabled(True)
        try:
            check_external_tools()

            print("Running VoxAlign MNI Lookup!")
            print("\nOutput folder:", self.output_folder)
            print("\nT1 DICOM:", T1_dicom)
            for coord_row in MNI_coords:
                print(f"\nInput MNI coordinates: [{coord_row[0]}, {coord_row[1]}, {coord_row[2]}]")

            os.chdir(self.output_folder)

            T1_dicom_header = pydicom.dcmread(T1_dicom,stop_before_pixels=True)

            if self.nonlin_path:
                for file in self.required_files:
                    shutil.copy(os.path.join(self.nonlin_path,file),self.output_folder)
                
                #convert new T1 DICOM to NIFTI
                command = f"dcm2niix -f newT1 -o '{self.output_folder}' -s y {T1_dicom}"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)

                #skull strip session 1 T1
                print("\n...\n\nSkull stripping T1 ...")
                command = f"bet2 newT1.nii.gz newT1_ss.nii"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)

                # linearly register the new T1 to the one already registered to MNI space
                print("\n...\n\nLinearly registering new and existing T1s ...")
                command = "flirt -in T1_ss.nii.gz -ref newT1_ss.nii.gz -dof 6 -out T1tonewT1lin -omat T1tonewT1lin.mat"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)

            else:            
                #convert T1 DICOM to NIFTI
                command = f"dcm2niix -f T1 -o '{self.output_folder}' -s y {T1_dicom}"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)

                # crop neck from T1
                command = "robustfov -r croppedT1.nii -i T1.nii"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)

                #skull strip T1
                print("\n...\n\nSkull stripping T1 ...")
                command = f"bet2 croppedT1.nii.gz T1_ss.nii"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)

                # linearly register the T1 to MNI space
                print("\n...\n\nInitial linear registration to MNI space ...")
                command = "flirt -in T1_ss.nii.gz -ref $FSLDIR/data/standard/MNI152_T1_2mm_brain.nii.gz -dof 12 -out T1toMNIlin -omat T1toMNIlin.mat"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)

                # starting with the linear registration, now nonlinearly register to MNI space
                print("\n...\n\nFinal nonlinear registration to MNI space ...")
                if self.checkbox.isChecked():
                    # subsampling level controls how fast (but also how accurate) it is. fnirt default from T1_2_MNI152_2mm.cnf is --subsamp=4,4,2,2,1,1
                    command = "fnirt --in=croppedT1.nii.gz --aff=T1toMNIlin.mat --config=T1_2_MNI152_2mm.cnf --subsamp=8,8,8,4,2,1 --iout=T1toMNInonlin --cout=T1toMNI_coef --fout=T1toMNI_warp"
                    print("Running faster nonlinear registration to MNI space, using more aggressive subsampling")                
                else:
                    command = "fnirt --in=croppedT1.nii.gz --aff=T1toMNIlin.mat --config=T1_2_MNI152_2mm.cnf --iout=T1toMNInonlin --cout=T1toMNI_coef --fout=T1toMNI_warp"
                    print("Running long nonlinear registration to MNI space (using FSL subsampling defaults)")
                result = subprocess.run(command, shell=True, capture_output=True, text=True)

            filename='MNI_lookup_voxel_pos.txt'
            try:
                with open(filename, 'a') as file:
                    file.write(f"Study: {T1_dicom_header.StudyDescription}")
                    file.write(f"\nDate: {T1_dicom_header.StudyDate}")
                    file.write(f"\nParticipant: {T1_dicom_header.PatientID}")
                    file.write(f'\nT1 DICOM file: {Path(T1_dicom).name}')
                    if self.nonlin_path is not None:
                        regtext = "Used pre-run nonlinear registration to MNI space"
                    else:
                        if self.checkbox.isChecked():
                            regtext = "Fast nonlinear registration: subsampling 8,8,8,4,2,1"
                        else:
                            regtext = "Slow (default) nonlinear registration: subsampling 4,4,2,2,1,1"
                    file.write(f'\n{regtext}')
                    file.write(f"\n---------------------------")
            except Exception as e:
                print(f"Error writing to file: {e}")

            # given these warps, translate the input MNI coordinates to subject space
            for voxnum,coord_row in enumerate(MNI_coords):

                command = f"echo {coord_row[0]} {coord_row[1]} {coord_row[2]} | std2imgcoord -img T1_ss.nii.gz -std $FSLDIR/data/standard/MNI152_T1_2mm.nii.gz -warp T1toMNI_warp.nii.gz  -"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                new_coords = np.round(np.asarray(result.stdout.split(), dtype=float),1)

                if self.nonlin_path:
                    command = f"echo {new_coords[0]} {new_coords[1]} {new_coords[2]} | img2imgcoord -src T1_ss.nii.gz -dest newT1_ss.nii.gz -mm -xfm T1tonewT1lin.mat  -"
                    result = subprocess.run(command, shell=True, capture_output=True, text=True)
                    new_coords = np.round(np.asarray(result.stdout.split('\n')[1].split(), dtype=float),1)

                fslcolors = ['red','orange','yellow','green','blue','purple']
                
                # write out annotations file that FSL loads in to show crosshair(s) at selected coordinates
                # for current T1 (native space)
                native_annotations_txt = compose_fsl_annot_text(fslcolors,voxnum,new_coords)
                try:
                    with open('native_annotations.txt', 'a') as file:
                        file.write(native_annotations_txt)
                except Exception as e:
                    print(f"Couldn't save voxel position annotation for fsleyes: {e}")

                # also show the requested coordinates in MNI space
                MNI_annotations_txt = compose_fsl_annot_text(fslcolors,voxnum,coord_row)
                try:
                    with open('MNI_annotations.txt', 'a') as file:
                        file.write(MNI_annotations_txt)
                except Exception as e:
                    print(f"Couldn't save MNI position annotation for fsleyes: {e}")

                transvec = convert_signs_to_letters(np.round(new_coords,1))
                print("\n-------------")
                print(f"MNI Coordinates: {coord_row}")
                print(f'Position: {transvec}')

                try:
                    with open(filename, 'a') as file:
                        file.write(f"\n\n---------------------------")
                        file.write(f"\nMNI Coordinates: {coord_row}")
                        file.write(f'\nVoxel Position: {transvec}\n')
                        file.write(f"---------------------------")

                    print(f"Position written to {filename}")
                    print("-------------\n")
                except Exception as e:
                    print(f"Error writing to file: {e}")


            print("\nVoxAlign MNI lookup process completed successfully.\n")
            
            if self.nonlin_path:
                command = f"fsleyes -ixh --displaySpace world -a native_annotations.txt newT1.nii"
            else:
                command = f"fsleyes -ixh --displaySpace world -a native_annotations.txt croppedT1.nii.gz"
            process = subprocess.Popen(command, shell=True)
            
            command = f"fsleyes -ixh --displaySpace world -std1mm -a MNI_annotations.txt T1toMNInonlin.nii.gz"
            process = subprocess.Popen(command, shell=True)

            # Create and display the success message box
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.NoIcon)
            msg_box.setWindowTitle("Success")
            msg_box.setText("VoxAlign MNI lookup process completed successfully!")
            msg_box.setStandardButtons(QMessageBox.Ok)
            
            # If the user clicks "OK", close the application
            if msg_box.exec() == QMessageBox.Ok:
                self.close()  # Close the GUI window
                sys.exit()    # Exit the application

        except Exception as e:
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")
            print(f"An error occurred: {e}")

        finally:
            self.run_button.setDisabled(False)

def start_mnilookup():
    """Function to initialize and run the VoxAlign MNI Lookup PyQt application."""
    app = QApplication(sys.argv)
    window = MNILookupApp()
    window.show()
    sys.exit(app.exec_())