# KVM Control

[English](README_en.md) | [中文](README.md)

## Introduction

`KVM Control` stands for Keyboard Video Mouse Control. It is a tool that uses a Windows machine as an intermediary controller to operate a target machine. It offers the following features:

- No need for a network connection on the target machine
- No software installation required on the target machine
- No restriction on the target machine’s operating system
- Support for remote BIOS modification
- Automatic saving and restoring of the last connection
- Automatic scanning of serial ports and video streams
- One-click saving of the original image

Compared to similar solutions (such as KVM-OVER-IP or PI-KVM), which offer comprehensive features but require additional hardware purchases, this solution only requires two cables (approximately $15). With the help of an idle Windows machine, basic operations can be achieved.

## Mechanic

```
    User Machine
       ↑
       |
       |
    Ethernet (RDP, VNC)
       |
       |
       ↓
Intermediate Control Machine
    ↓         ↑
    |         |
 Serial  Video Capture Card
    |         |
    |         |
    |         |
  target machine

```

## Hardware
- USB HDMI Video Capture Card
- Dual USB Cable (CH340, CH9329)

## Software
On the intermediate machine, perform the following steps:
1. Install Python
2. Install the CH340 driver
3. Run `start.bat`

## Tips
1. Currently hard-coded to a `1920*1080` resolution. It is recommended to set the target machine’s resolution to `1920*1080` with 100% scaling. Future updates will adapt to other resolutions.
