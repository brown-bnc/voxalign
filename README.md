# voxalign
automated prescription of MRS voxels to match a previous scan session or based on MNI coordinate(s)

documentation available here: https://docs.ccv.brown.edu/bnc-user-manual/standalone-tools/automated-mr-spectroscopy-voxel-placement-with-voxalign 


## License

This project contains original code by Elizabeth Lorenc at Brown University and is licensed under the following terms:

> **Copyright 2025, Brown University, Providence, RI.**
>
> All Rights Reserved.
>
> Permission to use, copy, modify, and distribute this software and its documentation for any purpose other than its incorporation into a commercial product or service is hereby granted without fee, provided that the above copyright notice appear in all copies and that both that copyright notice and this permission notice appear in supporting documentation, and that the name of Brown University not be used in advertising or publicity pertaining to distribution of the software without specific, written prior permission.
>
> BROWN UNIVERSITY DISCLAIMS ALL WARRANTIES WITH REGARD TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR ANY PARTICULAR PURPOSE. IN NO EVENT SHALL BROWN UNIVERSITY BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

### Third-Party Code

This project also includes adapted code from the following open-source BSD-licensed software:

- [`hcpre`](https://github.com/beOn/hcpre) by Ben Acland  
  - Function: `dicom_orientation_string`  
  - License: BSD 3-Clause (custom attribution)

- [`nii2dcm`](https://github.com/tomaroberts/nii2dcm) by Tom Roberts  
  - Function: `calc_prescription_from_nifti`  
  - License: BSD 3-Clause

- [`Gannet3.0/GannetMask_SiemensRDA.m`](https://github.com/richardedden/Gannet3.0/blob/master/GannetMask_SiemensRDA.m) by Georg Oeltzschner  
  - Function: `calc_inplane_rot`  
  - Based on work by Rudolph Pienaar and Andre van der Kouwe  
  - License: BSD 3-Clause

Each of these components retains its original license, which is included in full in the [LICENSE](./LICENSE) file.
