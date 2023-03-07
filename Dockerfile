FROM python:3.9.6  # 基础镜像，构建镜像的开始，这里是python版本
COPY . / # 类似ADD，将我们文件拷贝到镜像中
WORKDIR ./ # 镜像的工作目录
RUN pip install -r ./requirements.txt # 镜像构建的时候需要运行的命令
EXPOSE 5000 # 暴露端口配置 实际取决于docker run 命令的选择
ENTRYPOINT ["python"] # 指定这个容器启动的时候要运行的命令，可以追加命令
CMD ["./dockertest.py"] # #指定这个容器启动的时候要运行的命令，只有最后一个会生效，可被替代