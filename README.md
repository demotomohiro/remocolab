# remocolab
remocolab is a Python module to allow remote access to [Google Colaboratory](https://colab.research.google.com/) using SSH or [TurboVNC](https://www.turbovnc.org/).
It also install [VirtualGL](https://www.virtualgl.org/) so that you can run OpenGL programs on a Google Colaboratory machine and see the screen on VNC client.
It secures TurboVNC connection using SSH port forwarding.

## Requirements
- You can use [Google Colaboratory](https://colab.research.google.com/)
  - That means you need Google acount and a browser that is supported by Google Colaboratory.
- [ngrok](https://ngrok.com/) Tunnel Authtoken
  - You need to sign up for ngrok to get it
- SSH client
- (Optional) TurboVNC Viewer if you use it.

## How to use
1. Create a new notebook on Google Colaboratory
2. Add a code cell and copy & paste one of following codes to the cell

- SSH only:
```python3
!pip install git+https://github.com/demotomohiro/remocolab.git
import remocolab
remocolab.setupSSHD()
```
Note: Use `remocolab.setupSSHD(use_ssh_key=True)` if you want the server to auto login with your public SSH keys (so you won't need specify which private key to go with which server). In this case, prepare a `authorized_keys` file like [this](https://gist.github.com/lamhoangtung/4fca574da11ef45869bdfea8062417b5/raw/ebdc8c6f8fca2162ae3665f91271bd1fc0fa99b6/authorized_keys)

- SSH and TurboVNC:
```python3
!pip install git+https://github.com/demotomohiro/remocolab.git
import remocolab
remocolab.setupVNC()
```

3. (Optional) If you want to run OpenGL applications or any programs that use GPU,
Click "Runtime" -> "Change runtime type" in top menu and change Hardware accelerator to GPU. 
4. Run that cell
5. Then the message that ask you to copy & paste tunnel authtoken of ngrok will appear.
Login to ngrok, click Auth on left side menu, click Copy, return to Google Colaboratory, paste it to the text box under the message and push enter key.
6. Select your ngrok region. Select the one closest to your location. For example, if you were in Japan, type jp and push enter key.
7. remocolab setup ngrok and SSH server. Please wait for it done (about 2 minutes)
8. Then, root and colab user password and ssh command to connect the server will appear.
9. Copy & paste the ssh command to your terminal and login to the server using displayed colab user password.
(Even if you just want to use TurboVNC, you need to login using SSH to make SSH port forwarding)

* If you use TurboVNC:
10. Wait for remocolab setup TurboVNC (about 2 minutes)
11. When VNC password is displayed, run TurboVNC server, set server address to ``localhost:1`` and connect
12. Then, password will be asked. Copy & paste that VNC password to your TurboVNC viewer.

## How to run OpenGL applications
Put the command to run the OpenGL application after ``vglrun``.
For example, ``vglrun firefox`` runs firefox and you can watch web sites using WebGL with hardware acceleration.
