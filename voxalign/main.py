import numpy as np
import nibabel as nib
import tkinter as tk
from tkinter import filedialog, scrolledtext
import glob
import subprocess
import os
np.set_printoptions(suppress=True)
from pathlib import Path
import sys
from voxalign.utils import check_external_tools, calc_inplane_rot, dicom_orientation_string


# Variables to store selected paths
output_folder = ""
session1_T1_dicom = ""
session2_T1_dicom = ""
selected_spectroscopy_files = []


def select_output_folder():
    global output_folder
    output_folder = filedialog.askdirectory()
    if output_folder:
        output_label.config(state=tk.NORMAL)
        output_label.delete(1.0, tk.END)
        output_label.insert(tk.END, output_folder)
        output_label.config(state=tk.DISABLED)
    else:
        output_label.config(state=tk.NORMAL)
        output_label.delete(1.0, tk.END)
        output_label.insert(tk.END, "No folder selected")
        output_label.config(state=tk.DISABLED)

def select_session1_T1_dicom():
    global session1_T1_dicom
    session1_T1_dicom = filedialog.askopenfilename(title="Select Session 1 T1 DICOM", filetypes=[("DICOM files", "*.dcm")])
    if session1_T1_dicom:
        session1_T1_label.config(state=tk.NORMAL)
        session1_T1_label.delete(1.0, tk.END)
        session1_T1_label.insert(tk.END, session1_T1_dicom)
        session1_T1_label.config(state=tk.DISABLED)
    else:
        session1_T1_label.config(state=tk.NORMAL)
        session1_T1_label.delete(1.0, tk.END)
        session1_T1_label.insert(tk.END, "No file selected")
        session1_T1_label.config(state=tk.DISABLED)

def select_session2_T1_dicom():
    global session2_T1_dicom
    session2_T1_dicom = filedialog.askopenfilename(title="Select Session 2 T1 DICOM", filetypes=[("DICOM files", "*.dcm")])
    if session2_T1_dicom:
        session2_T1_label.config(state=tk.NORMAL)
        session2_T1_label.delete(1.0, tk.END)
        session2_T1_label.insert(tk.END, session2_T1_dicom)
        session2_T1_label.config(state=tk.DISABLED)
    else:
        session2_T1_label.config(state=tk.NORMAL)
        session2_T1_label.delete(1.0, tk.END)
        session2_T1_label.insert(tk.END, "No file selected")
        session2_T1_label.config(state=tk.DISABLED)

def select_session1_spectroscopy_dicoms():
    global selected_spectroscopy_files
    new_files_selected = filedialog.askopenfilenames(title="Select Session 1 Spectroscopy DICOMs", filetypes=[("DICOM files", "*.dcm")])
    
    # Append new files to the existing list
    if new_files_selected:
        selected_spectroscopy_files.extend(new_files_selected)
        
        # Remove duplicates (optional)
        selected_spectroscopy_files = list(set(selected_spectroscopy_files))
        
        session1_spec_label.config(state=tk.NORMAL)
        session1_spec_label.delete(1.0, tk.END)
        session1_spec_label.insert(tk.END, ', '.join(selected_spectroscopy_files))
        session1_spec_label.config(state=tk.DISABLED)
    else:
        if not selected_spectroscopy_files:
            session1_spec_label.config(state=tk.NORMAL)
            session1_spec_label.delete(1.0, tk.END)
            session1_spec_label.insert(tk.END, "No files selected")
            session1_spec_label.config(state=tk.DISABLED)
            
def run_voxalign():
    # this keeps them from accidentally clicking twice
    run_button.config(state=tk.DISABLED)

    try:
        check_external_tools()

        print("Running VoxAlign!")
        print("\nOutput folder:", output_folder)
        print("\nSession 1 T1 DICOM:", session1_T1_dicom)
        print("\nSession 2 T1 DICOM:", session2_T1_dicom)
        print("\nSession 1 Spectroscopy DICOMs:", selected_spectroscopy_files)

        os.chdir(output_folder)

        #convert session 1 T1 DICOM to NIFTI
        command = f"dcm2niix -f sess1_T1 -o {output_folder} -s y {session1_T1_dicom}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        #skull strip session 1 T1
        print("\n...\nSkull stripping session 1 T1 ...")
        command = f"bet2 sess1_T1.nii sess1_T1_ss.nii"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        # Convert session 2 T1 DICOM to NIFTI
        command = f"dcm2niix -f sess2_T1 -o {output_folder} -s y {session2_T1_dicom}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        #skull strip session 2 T1
        print("Skull stripping session 2 T1 ...")
        command = f"bet2 sess2_T1.nii sess2_T1_ss.nii"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        # use flirt to register session 1 T1 to session 2 T1
        print("Aligning session 1 T1 to session 2 T1 ...")
        command = f"flirt -in sess1_T1_ss.nii.gz -ref sess2_T1_ss.nii.gz -out sess1_T1_aligned -omat sess1tosess2.mat -dof 6"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        # Convert session 1 spectroscopy DICOM(s)  to NIFTI
        for dcm in selected_spectroscopy_files:
            #File names can be specified with the -f option and output directories with the -o option.
            command = f"spec2nii 'dicom' -o sess1_svs {dcm}"
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

        spec_niftis = glob.glob('sess1_svs/*')

        for nii in spec_niftis:
            roi=Path(nii.removesuffix(''.join(Path(nii).suffixes))).stem
            spec_nii = nib.load(nii)
            sess1_nii = nib.load('sess1_T1.nii')
            sess2_nii = nib.load('sess2_T1.nii')

            sess1to2affine = np.loadtxt('sess1tosess2.mat')

            # combine affine transforms to go from sess 1 T1 -> sess 2 T1 and tweak a bit in case autoalign didn't do the trick
            transform = sess1to2affine @ sess2_nii.affine @ np.linalg.inv(sess1_nii.affine) 
            new_affine = transform @ spec_nii.affine 

            aligned_spec = nib.load(nii) #start with session 1 spec nifti
            aligned_spec.set_sform(new_affine,code='aligned')
            aligned_spec.set_qform(new_affine,code='unknown')
            nib.save(aligned_spec,f'{roi}_aligned.nii.gz')

            dimX, dimY, dimZ = spec_nii.header['pixdim'][1], spec_nii.header['pixdim'][2], spec_nii.header['pixdim'][3]

            # slice positioning in 3-D space
            # nb: -1 for dir cosines gives consistent orientation between Nifti and DICOM in ITK-Snap
            A = spec_nii.affine
            rotmat,transvec = nib.affines.to_matvec(A)
            dircosX = -1*rotmat[:3, 0] / dimX
            dircosY = -1*rotmat[:3, 1] / dimY
            dircosZ = rotmat[:3, 2] / dimZ #this is the same as np.cross(dircosX,dircosY)
            transvec[:2]*=-1 

            nii_orientation_matrix=np.vstack([dircosZ,dircosY,dircosX])
            nii_orientation_matrix[:,2]*=-1 #hacky because i don't know why but seems to work
            norm = nii_orientation_matrix[0,:]
            slice_orientation_pitch, _ = dicom_orientation_string(norm)

            inplane_rot = calc_inplane_rot(nii_orientation_matrix,slice_orientation_pitch.split(' > ')[0])

            print(f"\nSess 1 {roi} \n/Orientation: {slice_orientation_pitch}")
            print(f"In-plane rotation: {inplane_rot:.2f}")
            print(f'Voxel Position: {transvec}')

            #now do it for aligned sess 2 voxel
            dimX, dimY, dimZ = aligned_spec.header['pixdim'][1], aligned_spec.header['pixdim'][2], aligned_spec.header['pixdim'][3]

            # slice positioning in 3-D space
            # nb: -1 for dir cosines gives consistent orientation between Nifti and DICOM in ITK-Snap
            A = aligned_spec.affine
            rotmat,transvec = nib.affines.to_matvec(A)
            dircosX = -1*rotmat[:3, 0] / dimX
            dircosY = -1*rotmat[:3, 1] / dimY
            dircosZ = rotmat[:3, 2] / dimZ #this is the same as np.cross(dircosX,dircosY)
            transvec[:2]*=-1 

            nii_orientation_matrix=np.vstack([dircosZ,dircosY,dircosX])
            nii_orientation_matrix[:,2]*=-1 #hacky because i don't know why but testing to see if it works
            norm = nii_orientation_matrix[0,:]
            slice_orientation_pitch, _ = dicom_orientation_string(norm)

            inplane_rot = calc_inplane_rot(nii_orientation_matrix,slice_orientation_pitch.split(' > ')[0])

            # Define the file name based on the ROI
            filename = f"{roi}_prescription.txt"
            
            try:
                with open(filename, 'w') as file:
                    file.write(f"Sess 2 {roi} \nOrientation: {slice_orientation_pitch}\n")
                    file.write(f"In-plane rotation: {inplane_rot:.2f}\n")
                    file.write(f'Voxel Position: {transvec}\n')
                print(f"Data written to {filename}")
            except Exception as e:
                print(f"Error writing to file: {e}")

            print(f"\nSess 2 {roi} \nOrientation: {slice_orientation_pitch}")
            print(f"In-plane rotation: {inplane_rot:.2f}")
            print(f'Voxel Position: {transvec}')

        command = "fsleyes sess1_T1.nii sess1_svs/*.nii.gz sess2_T1.nii *aligned.nii.gz"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)   

    except Exception as e:
        print(f"An error occurred: {e}")
        # Re-enable the button if an error occurs
        run_button.config(state=tk.NORMAL)
        return

    print("\nVoxAlign process completed successfully.\n")

    # Close the Tkinter window
    root.destroy()
    
    # Exit the program after closing the window
    sys.exit()

# Create the main window
root = tk.Tk()
root.title("VoxAlign DICOM Selector")
root.geometry("800x400")  # Set a fixed size for the window to prevent it from becoming too large

# Output folder selection
output_button = tk.Button(root, text="Select Output Folder", command=select_output_folder)
output_button.pack(pady=5)
output_label = scrolledtext.ScrolledText(root, height=2, width=70, wrap=tk.WORD, state=tk.DISABLED)
output_label.pack(pady=5)

# Session 1 T1 DICOM selection
session1_T1_button = tk.Button(root, text="Select Session 1 T1 DICOM", command=select_session1_T1_dicom)
session1_T1_button.pack(pady=5)
session1_T1_label = scrolledtext.ScrolledText(root, height=2, width=70, wrap=tk.WORD, state=tk.DISABLED)
session1_T1_label.pack(pady=5)

# Session 2 T1 DICOM selection
session2_T1_button = tk.Button(root, text="Select Session 2 T1 DICOM", command=select_session2_T1_dicom)
session2_T1_button.pack(pady=5)
session2_T1_label = scrolledtext.ScrolledText(root, height=2, width=70, wrap=tk.WORD, state=tk.DISABLED)
session2_T1_label.pack(pady=5)

# Session 1 Spectroscopy DICOMs selection
session1_spec_button = tk.Button(root, text="Add Session 1 Spectroscopy DICOMs", command=select_session1_spectroscopy_dicoms)
session1_spec_button.pack(pady=5)
session1_spec_label = scrolledtext.ScrolledText(root, height=4, width=70, wrap=tk.WORD, state=tk.DISABLED)
session1_spec_label.pack(pady=5)

# "Run VoxAlign" button
run_button = tk.Button(root, text="Run VoxAlign", command=run_voxalign)
run_button.pack(pady=5)
status_label = tk.Label(root, text="  ")
status_label.pack()

# Start the Tkinter event loop
root.mainloop()
