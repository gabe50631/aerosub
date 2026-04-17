# Project-Aertic
A remote control submarine project. 

# SolidWorks CAD Collaboration Guidelines

This repository is used to store and collaborate on SolidWorks CAD files. Because CAD files are binary and cannot be merged like code, the following rules must be followed to avoid broken references or lost work.

- Install Git LFS: https://git-lfs.com/ before working on this

## Folder Structure

TBD

### Important: SolidWorks relies on relative file paths. Moving or renaming files can break assemblies.

## File Ownership Rule
- Only ONE person may edit a CAD file at a time
- CAD files cannot be merged
- Always coordinate before editing shared assemblies
- Confirm nobody else is working on a file before editing
- Can lock a file with *git lfs lock path/to/file.SLDPRT*
- Can unlock a file with *git lfs unlock path/to/file.SLDPRT*

## Committing
Use Pack and Go for new or major assemblies: File → Pack and Go → Save to repository folder
Commit all referenced files together



## What NOT To Do
- Do not edit the same file as someone else
- Do not force-push to main
- Do not rename or move files casually
- Do not commit temporary SolidWorks files
