# linux-lens

### this is a simple copy of google lens for linux and windows using python
---
The main use of this project is to do a simple image search without all the trouble of opening browser and so on.<br><br> This uses python with some GUI stuff and pillow to help search image using a temp host and an image manipulation website which help search image across multiple image search option like google, bing, Yandex and so on <br> later on i will/try to added some extra into it since why not?<br> Such as a OCR so you can extract sensitive text without worry.<br>I am planning on adding more into it later on as I do on 


- Bullet point of what's above:
    * uses python with tk, customtk, pillow, requests 
    * ocr ( using easyocr)
     image to search (Using a temp host and a multitool image manipulation website)
    * the package and stuff can be setup easily using poetry
    * for Windows users the main code doesn't interact with the system much at all so if you run this properly work (i am 60% sure)


## demo video
[demo viedo link (hosted on catbox)](https://files.catbox.moe/dv47pl.mp4)

- ps( the qulity and speed is bad since i dont have a power lap to work on (my intel is crying right now))


## how to set up:
1. install `poetry`. best way is to use `pipx`
```bash
pipx install poetry
```
<details>
<summary>linux</summary>

-  if you want you can make this into a bin file (tho i won't recommend it since It's pretty big around 500+MB or so)

- otherwise use the run.sh file ( make it a executable before doing so)
```bash
chmod +x run.sh 
```
   * ho add the cd of the location of the main file btw in the `run.sh` in the cd 

if you using `KDE` you can set it up as a shortcut to run it faster 
</details>
<details>
<summary>win</summary>
For windows ( i haven't used windows in a long time so i can't tell you how to)
but i know it works since it's just a python script without much system interaction
</details>
<br>


- # bugs that i have to fix:
    - [ ] the easyosr loading is slow so it makes the main tk load slower 
    - [ ] make the osr even better at text formatting
