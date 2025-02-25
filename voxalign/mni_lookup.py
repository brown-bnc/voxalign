import numpy as np
import nibabel as nib
import glob
import subprocess
import os
np.set_printoptions(suppress=True)
from pathlib import Path
import sys
from voxalign.utils import check_external_tools, calc_prescription_from_nifti, convert_signs_to_letters, get_unique_filename, vox_to_scaled_FSL_vox
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

class MNILookupApp(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setWindowTitle("MNI Lookup DICOM Selector")
        self.setGeometry(100, 100, 600, 400)
        layout = QVBoxLayout()

        # Output folder selection
        self.output_button = QPushButton("Select Output Folder", self)
        self.output_button.clicked.connect(self.select_output_folder)
        layout.addWidget(self.output_button)

        self.output_label = QTextEdit(self)
        self.output_label.setReadOnly(True)
        layout.addWidget(self.output_label)
        layout.addSpacing(20)

        # Session 1 T1 DICOM selection
        self.T1_button = QPushButton("Select T1 DICOM", self)
        self.T1_button.clicked.connect(self.select_T1_dicom)
        layout.addWidget(self.T1_button)

        self.T1_label = QTextEdit(self)
        self.T1_label.setReadOnly(True)
        layout.addWidget(self.T1_label)
        layout.addSpacing(20)

        # Instruction label
        self.label = QLabel("Enter MNI coordinate(s):", self)
        layout.addWidget(self.label)
        
        # Container for input fields (stores rows dynamically)
        self.input_container = QVBoxLayout()
        layout.addLayout(self.input_container)

        # List to keep track of input row references
        self.rows = []
        self.add_row()        
        
        # Button to add new rows
        self.add_button = QPushButton("Add another MNI coordinate", self)
        self.add_button.clicked.connect(self.add_row)
        layout.addWidget(self.add_button)
        layout.addSpacing(20)

        self.checkbox = QCheckBox("Use longer, more accurate registration to MNI space", self)
        self.checkbox.stateChanged.connect(self.checkbox_changed)  # Connect state change
        layout.addWidget(self.checkbox)
        layout.addSpacing(20)

        # Calculate voxel position button
        self.run_button = QPushButton("Calculate voxel position", self)
        self.run_button.clicked.connect(lambda: (self.validate_MNI_input(), self.run_voxalign_MNI_lookup()))
        layout.addWidget(self.run_button)

        self.setLayout(layout)


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

        # Button to remove the row
        delete_button = QPushButton("❌", self)
        delete_button.setFixedSize(50, 50)
        delete_button.setStyleSheet("border : none") 
        delete_button.clicked.connect(partial(self.remove_row, row_layout, num1_input, num2_input, num3_input, delete_button))

        # Add widgets to the row layout
        row_layout.addWidget(num1_input)
        row_layout.addWidget(num2_input)
        row_layout.addWidget(num3_input)
        row_layout.addWidget(delete_button)

        # Add the row layout to the vertical container
        self.input_container.addLayout(row_layout)

        # Store row reference in the list
        self.rows.append((num1_input, num2_input, num3_input, delete_button,row_layout))

    def remove_row(self, row_layout, num1_input, num2_input, num3_input, delete_button):
        """Removes a row from the layout and deletes widgets properly."""

        # Safely delete all widgets in the row
        num1_input.deleteLater()
        num2_input.deleteLater()
        num3_input.deleteLater()
        delete_button.deleteLater()  # Ensure the delete button itself is removed

        # Remove the row layout itself
        row_layout.deleteLater()

        # Remove row from the tracking list
        self.rows = [row for row in self.rows if row[4] != row_layout]

    def validate_MNI_input(self):
        """Validate the input from the three number fields."""
        global MNI_coords
        MNI_coords = []
        for num1_input, num2_input, num3_input, _, _ in self.rows:

            try:
                #global MNI_coords
                # Convert the inputs to integers
                num1 = int(num1_input.text())
                num2 = int(num2_input.text())
                num3 = int(num3_input.text())
                MNI_coords.append([num1, num2, num3])
                # QMessageBox.information(self, "Success", f"Valid input: [{num1}, {num2}, {num3}]")
            except ValueError:
                # Handle invalid input
                QMessageBox.critical(self, "Error", "Please enter valid integers in all fields.")
                return
            
    def checkbox_changed(self):
        # Handles the checkbox state change
        if self.checkbox.isChecked():
            QMessageBox.information(self, "Checkbox Checked", "The slower, more accurate nonlinear registration to MNI space takes about 4 minutes")
        else:
            QMessageBox.information(self, "Checkbox Unchecked", "The quick nonlinear registration to MNI space takes about 2 minutes")

    def select_output_folder(self):
        global output_folder
        output_folder = Path(QFileDialog.getExistingDirectory(self, "Select Output Folder"))
        if output_folder:
            self.output_label.setText(str(output_folder))
        else:
            self.output_label.setText("No folder selected")

    def select_T1_dicom(self):
        global T1_dicom
        T1_dicom, _ = QFileDialog.getOpenFileName(self, "Select T1 DICOM", "", "DICOM files (*.dcm)")
        if T1_dicom:
            self.T1_label.setText(T1_dicom)
        else:
            self.T1_label.setText("No file selected")


    def run_voxalign_MNI_lookup(self):
        self.run_button.setDisabled(True)
        try:
            check_external_tools()

            print("Running VoxAlign MNI Lookup!")
            print("\nOutput folder:", output_folder)
            print("\nT1 DICOM:", T1_dicom)
            for coord_row in MNI_coords:
                print(f"\nInput MNI coordinates: [{coord_row[0]}, {coord_row[1]}, {coord_row[2]}]")

            os.chdir(output_folder)

            #convert session 1 T1 DICOM to NIFTI
            command = f"dcm2niix -f T1 -o '{output_folder}' -s y {T1_dicom}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            #skull strip session 1 T1
            print("\n...\n\nSkull stripping T1 ...")
            command = f"bet2 T1.nii T1_ss.nii"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            # linearly register the T1 to MNI space
            print("\n...\n\nInitial linear registration to MNI space ...")
            command = "flirt -in T1_ss.nii.gz -ref $FSLDIR/data/standard/MNI152_T1_2mm_brain.nii.gz -dof 12 -out T1toMNIlin -omat T1toMNIlin.mat"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            # starting with the linear registration, now nonlinearly register to MNI space
            print("\n...\n\nFinal nonlinear registration to MNI space ...")
            if self.checkbox.isChecked():
                # subsampling level controls how fast (but also how accurate) it is. fnirt default from T1_2_MNI152_2mm.cnf is --subsamp=4,4,2,2,1,1
                command = "fnirt --in=T1.nii --aff=T1toMNIlin.mat --config=T1_2_MNI152_2mm.cnf --iout=T1toMNInonlin --cout=T1toMNI_coef --fout=T1toMNI_warp"
                print("Running long nonlinear registration to MNI space (using FSL subsampling defaults)")
            else:
                command = "fnirt --in=T1.nii --aff=T1toMNIlin.mat --config=T1_2_MNI152_2mm.cnf --subsamp=8,8,8,4,2,1 --iout=T1toMNInonlin --cout=T1toMNI_coef --fout=T1toMNI_warp"
                print("Running faster nonlinear registration to MNI space, using more aggressive subsampling")
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            # given these warps, translate the input MNI coordinates to subject space
            for voxnum,coord_row in enumerate(MNI_coords):

                command = f"echo {coord_row[0]} {coord_row[1]} {coord_row[2]} | std2imgcoord -img T1.nii -std $FSLDIR/data/standard/MNI152_T1_2mm.nii.gz -warp T1toMNI_warp.nii.gz  -"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                new_coords = np.round(np.asarray(result.stdout.split(), dtype=float),1)

                fslcolors = ['red','orange','yellow','green','blue','purple']
                
                annotations_txt = f"X Point colour={fslcolors[voxnum]} lineWidth=4 honourZLimits=True zmin={new_coords[0]-2} zmax={new_coords[0]+2} x={new_coords[1]} y={new_coords[2]} \
                                    \nY Point colour={fslcolors[voxnum]} lineWidth=4 honourZLimits=True zmin={new_coords[1]-2} zmax={new_coords[1]+2} x={new_coords[0]} y={new_coords[2]} \
                                    \nZ Point colour={fslcolors[voxnum]} lineWidth=4 honourZLimits=True zmin={new_coords[2]-2} zmax={new_coords[2]+2} x={new_coords[0]} y={new_coords[1]}\n"
                try:
                    with open('annotations.txt', 'a') as file:
                        file.write(annotations_txt)
                except Exception as e:
                    print(f"Couldn't save voxel position annotation for fsleyes: {e}")

                transvec = convert_signs_to_letters(np.round(new_coords,1))
                print("\n-------------")
                print(f"MNI Coordinates: {coord_row}")
                print(f'Position: {transvec}')

                filename='MNI_lookup_voxel_pos.txt'
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
            
            command = f"fsleyes -ixh --displaySpace world -a annotations.txt T1.nii"
            process = subprocess.Popen(command, shell=True)
            
            command = f"fsleyes -ixh -std1mm T1toMNInonlin.nii.gz"
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
    """Function to initialize and run the VoxAlign PyQt application."""
    app = QApplication(sys.argv)
    window = MNILookupApp()
    window.show()
    sys.exit(app.exec_())