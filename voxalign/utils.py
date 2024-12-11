import os
import sys
import shutil
import numpy as np
import math
import nibabel as nib
from pathlib import Path

def get_unique_filename(filename,extension):
    path = Path(filename+extension)
    counter = 2
    while path.exists():
        path = Path(f"{filename}_{counter}{extension}")
        counter += 1
    return str(path)

def check_external_tools():
    """Check if FSL, dcm2niix, and spec2nii are installed and available."""
    # Check if FSL is installed
    if os.getenv('FSLDIR') is None:
        print("Error: FSLDIR environment variable is not set. Please install FSL and set FSLDIR.")
        sys.exit(1)

    if shutil.which("flirt") is None or shutil.which("bet2") is None:
        print("Error: FSL commands (flirt or bet2) not found in PATH.")
        sys.exit(1)

    # Check if dcm2niix is available
    if shutil.which("dcm2niix") is None:
        print("Error: dcm2niix is not installed or not found in PATH.")
        sys.exit(1)

    # Check if spec2nii is available
    if shutil.which("spec2nii") is None:
        print("Error: spec2nii is not installed or not found in PATH.")
        sys.exit(1)

    print("All external dependencies (FSL, dcm2niix, spec2nii) are installed.")

def calc_inplane_rot(orientation_matrix, vox_orient):
    norm = orientation_matrix[0,:]
    phase = np.empty(3)
    if vox_orient[0]=='T': #for transversal voxel orientation, the phase reference vector lies in the sagittal plane
        phase[0]=0
        phase[1]=norm[2]*np.sqrt(1/(norm[1]*norm[1]+norm[2]*norm[2]))
        phase[2]=-norm[1]*np.sqrt(1/(norm[1]*norm[1]+norm[2]*norm[2]))
    elif vox_orient[0]=='C': #for coronal voxel orientation, the phase reference vector lies in the transversal plane
        phase[0]=norm[1]*np.sqrt(1/(norm[0]*norm[0]+norm[1]*norm[1]))
        phase[1]=-norm[0]*np.sqrt(1/(norm[0]*norm[0]+norm[1]*norm[1]))
        phase[2]=0
    elif vox_orient[0]=='S': #for sagittal voxel orientation, the phase reference vector lies in the transversal plane
        phase[0]=-norm[1]*np.sqrt(1/(norm[0]*norm[0]+norm[1]*norm[1]))
        phase[1]=norm[0]*np.sqrt(1/(norm[0]*norm[0]+norm[1]*norm[1]))
        phase[2]=0
    else:
        raise Exception("Unable to determine voxel orientation")

    phaseRot = orientation_matrix[1,:].T
    if np.dot(np.cross(phase,phaseRot),norm) <=0:
        inplane_rot = np.degrees(np.arccos(np.dot(phase,phaseRot)))
    else:
        inplane_rot = -np.degrees(np.arccos(np.dot(phase,phaseRot)))
    
    return inplane_rot

# adapted from https://github.com/beOn/hcpre/blob/master/hcpre/duke_siemens/util_dicom_siemens.py#L540
# License: https://github.com/beOn/hcpre/blob/master/License.txt
def dicom_orientation_string(normal):
    """Given a 3-item list (or other iterable) that represents a normal vector
    to the "imaging" plane, this function determines the orientation of the
    vector in 3-dimensional space. It returns a tuple of (angle, orientation)
    in which angle is e.g. "Tra" or "Tra>Cor -6" or "Tra>Sag 14.1 >Cor 9.3"
    and orientation is e.g. "Sag" or "Cor-Tra".

    For double angulation, errors in secondary angle occur that may be due to
    rounding errors in internal Siemens software, which calculates row and
    column vectors.
    """
    # docstring paraphrases IDL comments
    TOLERANCE = 1.e-4
    orientations = ('Sagittal', 'Coronal', 'Transverse')

    final_angle = ""
    final_orientation = ""

    # [IDL] evaluate orientation of normal vector:
    #
    # Find principal direction of normal vector (i.e. axis with its largest
    # component)
    # Find secondary direction (second largest component)
    # Calc. angle btw. projection of normal vector into the plane that
    #     includes both principal and secondary directions on the one hand
    #     and the principal direction on the other hand ==> 1st angulation:
    #     "principal>secondary = angle"
    # Calc. angle btw. projection into plane perpendicular to principal
    #     direction on the one hand and secondary direction on the other
    #     hand ==> 2nd angulation: "secondary>third dir. = angle"


    # get principal, secondary and ternary directions
    # Elizabeth added abs
    sorted_normal = sorted(normal,key=abs)

    for i, value in enumerate(normal):
        if value == sorted_normal[2]:
            # [IDL] index of principal direction
            principal = i
        if value == sorted_normal[1]:
            # [IDL] index of secondary direction
            secondary = i
        if value == sorted_normal[0]:
            # [IDL] index of ternary direction
            ternary = i

    # [IDL] calc. angle between projection into third plane (spawned by
    # principle & secondary directions) and principal direction:
    angle_1 = np.degrees(math.atan2(normal[secondary], normal[principal]))

    # [IDL] calc. angle btw. projection on rotated principle direction and
    # secondary direction:
    # projection on rotated principle dir.
    new_normal_ip = math.sqrt((normal[principal] ** 2) + (normal[secondary] ** 2))

    angle_2 = np.degrees(math.atan2(normal[ternary], new_normal_ip))

    # [IDL] SIEMENS notation requires modifications IF principal dir. indxs SAG !
    # [PS] In IDL, indxs is the name of the variable that is "secondary" here.
    #      Even with that substitution, I don't understand the comment above.
    # if not principal:
    #     if abs(angle_1) > 0:
    #         sign1 = angle_1 / abs(angle_1)
    #     else:
    #         sign1 = 1.0

    #     angle_1 -= (sign1 * 180.0)
    #     angle_2 *= -1
    
    if (abs(angle_2) < TOLERANCE) or (abs(abs(angle_2) - 180) < TOLERANCE):
        if (abs(angle_1) < TOLERANCE) or (abs(abs(angle_1) - 180) < TOLERANCE):
            # [IDL] NON-OBLIQUE:
            final_angle = orientations[principal]
            final_orientation = final_angle #used to reference non-existant variable

        else:
            # [IDL] SINGLE-OBLIQUE:
            final_angle = "%s > %s%.1f" % \
                    (orientations[principal][0], orientations[secondary][0],
                     (-1 * angle_1)
                    )
            final_orientation = orientations[principal] + '-' + orientations[secondary]
    else:
        # [IDL] DOUBLE-OBLIQUE:
        final_angle = "%s > %s%.1f > %s%.1f" % \
                (orientations[principal][0], orientations[secondary][0],
                 (-1 * angle_1), orientations[ternary][0], (-1 * angle_2))
        final_orientation = "%s-%s-%s" % \
                (orientations[principal], orientations[secondary],
                 orientations[ternary])

    return final_angle, final_orientation

def calc_prescription_from_nifti(nii):
    # adapted from https://github.com/tomaroberts/nii2dcm/blob/b03b4aacce25eeb6a00756bdb47365034dced787/nii2dcm/nii.py
    dimX, dimY, dimZ = nii.header['pixdim'][1], nii.header['pixdim'][2], nii.header['pixdim'][3]

    # slice positioning in 3-D space
    # nb: -1 for dir cosines gives consistent orientation between Nifti and DICOM in ITK-Snap
    A = nii.affine
    rotmat,transvec = nib.affines.to_matvec(A)
    dircosX = -1*rotmat[:3, 0] / dimX 
    dircosY = -1*rotmat[:3, 1] / dimY 
    dircosZ = rotmat[:3, 2] / dimZ #this is the same as np.cross(dircosX,dircosY)

    nii_orientation_matrix=np.vstack([dircosZ,dircosY,dircosX])
    nii_orientation_matrix[:,2]*=-1 #hacky because i don't know why but testing to see if it works
    norm = nii_orientation_matrix[0,:]
    slice_orientation_pitch, _ = dicom_orientation_string(norm)
    inplane_rot = calc_inplane_rot(nii_orientation_matrix,slice_orientation_pitch.split(' > ')[0])

    return slice_orientation_pitch,inplane_rot,[int(np.rint(dimX)), int(np.rint(dimY)), int(np.rint(dimZ))]

def convert_signs_to_letters(transvec):
    directions=[['L','R'],['P','A'],['F','H']]
    lettervec = []
    for axis,t in enumerate(transvec):
        if t < 0:
            dir = directions[axis][0]
        else:
            dir = directions[axis][1]
        lettervec.append(f"{dir}{abs(t)}")
    pos = ' '.join(lettervec)
    return pos

