FROM mottosso/maya:2020



# # First install all the maya dependencies
# RUN yum install -y                   \
#     epel-release                     \
#     mesa-libGLw                      \
#     libXp                            \
#     gamin                            \
#     audiofile                        \
#     audiofile-devel                  \
#     xorg-x11-fonts-ISO8859-1-100dpi  \
#     xorg-x11-fonts-ISO8859-1-75dpi   \
#     compat-openssl10                 \
#     libpng15                         \
#     libnsl                           \
#     python2

# # RUN ln -s /usr/bin/python2.7 /usr/bin/python
