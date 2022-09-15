# remocolab
## [Using a remote desktop or SSH is now disallowed from Colab runtimes](https://research.google.com/colaboratory/faq.html)

remocolab is a Python module to allow remote access to [Google Colaboratory](https://colab.research.google.com/) using SSH or [TurboVNC](https://www.turbovnc.org/).
It also install [VirtualGL](https://www.virtualgl.org/) so that you can run OpenGL programs on a Google Colaboratory machine and see the screen on VNC client.
It secures TurboVNC connection using SSH port forwarding.

- [FAQ](https://github.com/demotomohiro/remocolab/wiki/Frequently-Asked-Questions)

## How to access SSH server running in colab?
~~**ngrok currently doesn't work!**~~ ngrok works now

You cannot directory login to the SSH server running on a colab instace.
remocolab uses third party service to access it from your PC.
You can choose [ngrok](https://ngrok.com/) or [Argo Tunnel](https://www.cloudflare.com/products/argo-tunnel/).
You don't need to buy paid plan.
Which service works faster can depend on where/when you are.
- ngrok
  - require that you sign up for an account.
  - You don't need to install specific software on client machine.
  - You need to copy and paste authtoken to colab everytime you run remocolab.
- Argo Tunnel
  - You don't need to create account. [Cloudflare provide free version](https://blog.cloudflare.com/a-free-argo-tunnel-for-your-next-project/)
  - You need to copy [cloudflared](https://developers.cloudflare.com/argo-tunnel/downloads) on your client PC.
  - You cannot specify argo tunnel server's region. They says the connection uses Argo Smart Routing technology to find the most performant path.

## Requirements
- You can use [Google Colaboratory](https://colab.research.google.com/)
  - That means you need Google acount and a browser that is supported by Google Colaboratory.
- SSH client
  - [How to get SSH client on Windows](https://github.com/demotomohiro/remocolab/wiki/Frequently-Asked-Questions#how-to-get-ssh-client-on-windows)
- (Optional) [TurboVNC Viewer](https://sourceforge.net/projects/turbovnc/files/) if you use it.

If you use ngrok:
  - [ngrok](https://ngrok.com/) Tunnel Authtoken
  - You need to sign up for ngrok to get it

If you use Argo Tunnel:
  - Download [cloudflared](https://developers.cloudflare.com/argo-tunnel/downloads) on your client PC and untar/unzip it.

## How to use
1. (Optional) Generate ssh authentication key
   - By using public key authentication, you can login to ssh server without copy&pasting a password.
   - example command to generate it with ssh-keygen:
   ```console
   ssh-keygen -t ecdsa -b 521
   ```
2. Create a new notebook on Google Colaboratory
3. Add a code cell and copy & paste one of following codes to the cell
   - If you use public key authentication, specify content of your public key to `public_key` argument of `remocolab.setupSSHD()` or `remocolab.setupVNC()` like `remocolab.setupSSHD(public_key = "ecdsa-sha2-nistp521 AAA...")`
   - add `tunnel = "ngrok"` if you use ngrok.
- SSH only:
```python3
!pip install git+https://github.com/demotomohiro/remocolab.git
import remocolab
remocolab.setupSSHD()
```

- SSH and TurboVNC:
```python3
!pip install git+https://github.com/demotomohiro/remocolab.git
import remocolab
remocolab.setupVNC()
```
4. (Optional) If you want to run OpenGL applications or any programs that use GPU,
Click "Runtime" -> "Change runtime type" in top menu and change Hardware accelerator to GPU. 
5. Run that cell
6. (ngrok only)Then the message that ask you to copy & paste tunnel authtoken of ngrok will appear.
Login to ngrok, click Auth on left side menu, click Copy, return to Google Colaboratory, paste it to the text box under the message and push enter key.
   - ngrok token must be kept secret.
   I understand people hate copy & pasting ngrok token everytime they use remocolab, but I don't know how to skip it without risking a security.
   If you could specify ngrok token to `remocolab.setupSSHD()` or `remocolab.setupVNC()`, you can save ngrok token to a notebook.
   Then, you might forget that your notebook contains it and share the notebook.
7. (ngrok only)Select your ngrok region. Select the one closest to your location. For example, if you were in Japan, type jp and push enter key.
   - You can also specify ngrok region to ``remocolab.setupSSHD()`` or ``remocolab.setupVNC()`` in the code like ``remocolab.setupSSHD(ngrok_region = "jp")``.
8. remocolab setup ngrok and SSH server (and desktop environment and TurboVNC server if you run setupVNC). Please wait for it done
   - `remocolab.setupSSHD()` takes about 2 minutes
   - `remocolab.setupVNC()` takes about 5 minutes
9. Then, root and colab user password and ssh command to connect the server will appear.
10. Copy & paste that ssh command to your terminal on your local machine and login to the server.
    - use displayed colab user's password if you dont use public key authentication
    - Even if you just want to use TurboVNC, you need to login using SSH to make SSH port forwarding

* If you use TurboVNC:
11. Run TurboVNC viewer on your local machine, set server address to ``localhost:1`` and connect.
12. Then, password will be asked. Copy & paste the VNC password displayed in `remocolab.setupVNC()`'s output to your TurboVNC viewer.

When you got error and want to rerun `remocolab.setupVNC()` or `remocolab.setupSSHD()`, you need to do `factory reset runtime` before rerun the command.
As you can run only 1 ngrok process with free ngrok account, running `remocolab.setupVNC/setupSSHD` will fail if there is another instace that already ran remocolab.
In that case, terminate another instance from `Manage sessions` screen.

## How to run OpenGL applications
Put the command to run the OpenGL application after ``vglrun``.
For example, ``vglrun firefox`` runs firefox and you can watch web sites using WebGL with hardware acceleration.

## How to mount Google Drive
remocolab can allow colab user reading/writing files on Google Drive.
If you just mount drive on Google Colaboratory, only root can access it.

Click the folder icon on left side of Google Colaboratory and click mount Drive icon.
If you got new code cell that contains python code "from google.colab import ...", create a new notebook, copy your code to it and mount drive same way.
On new notebook, you can mount drive without getting such code cell.
  - You can still mount google drive by clicking the given code cell, but it requres getting authorization code and copy&pasting it everytime you run your notebook.
  - If you mount google drive on new notebook, it automatically mount when your notebook connect to the instance.

Add `mount_gdrive_to` argument with directory name to `remocolab.setupSSHD()` or `remocolab.setupVNC()`.
For example:
```python
  remocolab.setupSSHD(mount_gdrive_to = "drive")
```
Then, you can access the content of your drive in `/home/colab/drive`.
You can also mount specific directory on your drive under colab user's home directory.
For example:
```python
  remocolab.setupSSHD(mount_gdrive_to = "drive", mount_gdrive_from = "My Drive/somedir")
```

## Arguments of `remocolab.setupSSHD()` and `remocolab.setupVNC()`
- `ngrok_region`
  Specify ngrok region like "us", "eu", "ap". [List of region](https://ngrok.com/docs#global-locations).
  This argument is ignored if you specified `tunnel = "argotunnel"`.
- `check_gpu_available`
  When it is `True`, it checks whether GPU is available and show warning in case GPU is not available.
- `tunnel`
  Specify which service you use to access ssh server on colab.
  It must be "ngrok" or "argotunnel". default value is "argotunnel".
- `mount_gdrive_to`
  Specify a directory under colab user's home directory which is used to mount Google Drive.
  If it was not specified, Google Drive is not mount under colab user's home directory.
  Specifying it without mounting Google Drive on Google Colaboratory is error.
- `mount_gdrive_from`
  Specify a path of existing directory on your Google Drive which is mounted on the directory specified by `mount_gdrive_to`.
  This argument is ignored when `mount_gdrive_to` was not specified.
- `public_key`
  Specify ssh public key if you want to use public key authentication.
## How to setup public key authentication for root login
If you want to login as root, use following code:
```python3
!mkdir /root/.ssh
with open("/root/.ssh/authorized_keys", 'w') as f:
  f.write("my public key")
!chmod 700 /root/.ssh
!chmod 600 /root/.ssh/authorized_keys
```
And replace user name colab in ssh command to root.

## Experimental kaggle support
- As Kaggle stops sesson right after running ssh server, kaggle is no longer supported.

~~remocolab in kaggle branch works on [Kaggle](https://www.kaggle.com/).~~
1. Create a new Notebook with Python language.
2. Set settings to:
   - Internet on
   - Docker to Latest Available
   - GPU on if you use TurboVNC
3. Add a code cell and copy & paste one of following codes to the cell

- SSH only:
```python3
!pip install git+https://github.com/demotomohiro/remocolab.git@kaggle
import remocolab
remocolab.setupSSHD()
```

- SSH and TurboVNC:
```python3
!pip install git+https://github.com/demotomohiro/remocolab.git@kaggle
import remocolab
remocolab.setupVNC()
```

4. Follow instructions from step 4 in above "How to use".
