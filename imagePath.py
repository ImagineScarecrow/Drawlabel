import os

root = r"C:\Users\jason.li\Desktop\culane数据集"
xp_118_path ="XP_1118_DCT"
xp_119_path = "XP_1119_DCT"
xp_1122_path = "XP_1122_DCT"
wuhan_rain_downsampe = "wuhan_rain_downsample_10"

D28_night2_downsample_10="D28_night2_downsample_10"
D28_night1_downsample_10='D28_night1_downsample_10'
cubeA400_night_downsample_10="cubeA400_night_downsample_10"
ddpai_s5_night_downsample_10="ddpai_s5_night_downsample_10"

targetfile = os.path.join(root,wuhan_rain_downsampe+".txt")
img_path = os.path.join(root,wuhan_rain_downsampe)
img_name = os.listdir(img_path)
count = 0
with open(targetfile, "w") as f:
    for img in img_name:
        if img.find("mark")==-1 and img.endswith(".jpg"):
            count += 1
            f.write(wuhan_rain_downsampe+'/'+img+"\n")
            #f.write("\r\n")
    print("img number:{}".format(count))
