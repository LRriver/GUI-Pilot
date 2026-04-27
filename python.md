python环境使用conda 的moon_zx环境，已经预先安装基础的环境保了，激活只需要输入conda activate moon_zx,如果你需要新的包可以直接安装，并在提交的代码包里更新requirement.txt.
base) lzj@lzjdeMacBook-Pro refer_pro % conda env list

# conda environments:
#
# * -> active
# + -> frozen
base                 *   /Users/lzj/miniconda3
moon_zx                  /Users/lzj/miniconda3/envs/moon_zx

(base) lzj@lzjdeMacBook-Pro refer_pro % conda activate moon_zx
(moon_zx) lzj@lzjdeMacBook-Pro refer_pro % pip list
Package           Version
----------------- ------------
annotated-types   0.7.0
anyio             4.12.1
certifi           2026.2.25
contourpy         1.3.2
cycler            0.12.1
distro            1.9.0
et_xmlfile        2.0.0
exceptiongroup    1.3.1
fonttools         4.61.1
h11               0.16.0
httpcore          1.0.9
httpx             0.28.1
idna              3.11
jiter             0.13.0
kiwisolver        1.4.9
matplotlib        3.10.8
numpy             2.2.6
openai            2.24.0
openpyxl          3.1.5
packaging         26.0
pandas            2.3.3
pillow            12.1.1
pip               26.0.1
pydantic          2.12.5
pydantic_core     2.41.5
pyparsing         3.3.2
python-dateutil   2.9.0.post0
pytz              2026.1.post1
setuptools        82.0.1
six               1.17.0
sniffio           1.3.1
tqdm              4.67.3
typing_extensions 4.15.0
typing-inspection 0.4.2
tzdata            2025.3
wheel             0.46.3