FROM python:3
ADD . /

RUN pip install lark-parser
RUN pip install jinja2

RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y flex bison

RUN git clone https://github.com/cs-au-dk/MONA.git
WORKDIR MONA
RUN ./configure
RUN make
RUN make install-strip

WORKDIR /

RUN ldconfig

RUN rm -rf /var/lib/apt/lists/*

CMD ["python", "./main.py", "-s",\
  "./examples/left-hander-philosopher.sys",\
  "./examples/left-hander-philosopher-remembering-forks.sys",\
  "./examples/two-global-forks.sys",\
  "./examples/exclusive-task.sys",\
  "./examples/semaphore.sys",\
  "./examples/burns.sys",\
  "./examples/preemptive-task-arbitrary.sys",\
  "./examples/preemptive-task-highest.sys",\
  "./examples/dijkstra-scholten.sys"]
