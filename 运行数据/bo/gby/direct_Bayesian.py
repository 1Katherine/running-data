import pandas as pd
import numpy as np
import datetime
import joblib
import matplotlib.pyplot as plt
import shutil
import os
import time
from bayes_opt.logger import JSONLogger
from bayes_opt.event import Events
from bayes_opt import BayesianOptimization
from bayes_opt import SequentialDomainReductionTransformer



# 服务器运行spark时config文件
config_run_path = "/usr/local/home/gby/result/wordcount-100G/"
# 重要参数
vital_params_path = "/usr/local/home/gby/parameters_set.txt"
# 维护的参数-范围表
conf_range_table = "/usr/local/home/gby/Spark_conf_range_wordcount.xlsx"
# 保存配置
generation_confs = "/usr/local/home/gby/generationDomainConf.csv"





def black_box_function(**params):
    i=[]
    for conf in vital_params['vital_params']:
        i.append(params[conf])
        # print(key)
    # print(i)
    # print(y)

    return -schafferRun(i)


# 格式化参数配置：精度、单位等
def formatConf(conf, value):
    res = ''
    # 处理精度
    if confDict[conf]['pre'] == 1:
        res = round(value)
    elif confDict[conf]['pre'] == 0.01:
        res = round(value, 2)
    # 添加单位
    if not pd.isna(confDict[conf]['unit']):
        # 布尔值
        if confDict[conf]['unit'] == 'flag':
            res = str(bool(res)).lower()
        # 列表形式的参数（spark.serializer、spark.io.compression.codec等）
        elif confDict[conf]['unit'] == 'list':
            rangeList = confDict[conf]['Range'].split(' ')
            res = rangeList[int(res)]
        # 拼接上单位
        else:
            res = str(res) + confDict[conf]['unit']
    else:
        res = str(res)
    return res

# 1、单个配置 p写入到 /usr/local/home/zwr/hibench-spark-config/wordcount-100G-ga   命名：config1
# 2、run获取执行时间并返回
last_runtime = 1.0
def run(configNum):
    # configNum = None
    # 使用给定配置运行spark
    run_cmd = '/usr/local/home/zwr/wordcount-100G-ga.sh ' + str(configNum)
    os.system(run_cmd)
    # 睡眠3秒，保证hibench.report文件完成更新后再读取运行时间
    time.sleep(3)
    # 获取此次spark程序的运行时间
    get_time_cmd = 'tail -n 1 /usr/local/home/hibench/hibench/report/hibench.report'
    line = os.popen(get_time_cmd).read()
    runtime = float(line.split()[4])
    global last_runtime
    if runtime == last_runtime:
        rumtime = 100000.0
    else:
        last_runtime = runtime
    return runtime




# 1、实际运行
configNum = 1
def schafferRun(p):
    global configNum
    # 打开配置文件模板
    fTemp = open('configTemp', 'r')
    # 复制模板，并追加配置
    fNew = open(config_run_path + 'config' + str(configNum), 'a+')
    shutil.copyfileobj(fTemp, fNew, length=1024)
    try:
        for i in range(len(p)):
            fNew.write(' ')
            fNew.write(vital_params['vital_params'][i])
            fNew.write('\t')
            fNew.write(formatConf(vital_params['vital_params'][i], p[i]))
            fNew.write('\n')
    finally:
        fNew.close()
    runtime = run(configNum)
    configNum += 1
    return runtime


# 读取重要参数
vital_params = pd.read_csv(vital_params_path)
    # 参数范围和精度，从参数范围表里面获取


sparkConfRangeDf = pd.read_excel(conf_range_table)
sparkConfRangeDf.set_index('SparkConf', inplace=True)
confDict = sparkConfRangeDf.to_dict('index')


    # 遍历训练数据中的参数，读取其对应的参数空间
d1={}
d2={}
precisions = []  # 参数精度
for conf in vital_params['vital_params']:
    if conf in confDict:
        d1 = {conf: (confDict[conf]['min'], confDict[conf]['max'])}
        d2.update(d1)
        precisions.append(confDict[conf]['pre'])
    else:
        print(conf,'-----参数没有维护: ', '-----')

#print(d2)
# 确定其他参数
startTime = datetime.datetime.now()



bounds_transformer = SequentialDomainReductionTransformer()

#定义贝叶斯优化模型 
optimizer = BayesianOptimization(
        f=black_box_function,
        pbounds=d2,
        verbose=2,
        random_state=1,
        bounds_transformer=bounds_transformer
    )
logger = JSONLogger(path="./logs.json")
optimizer.subscribe(Events.OPTIMIZATION_STEP, logger)

optimizer.maximize(init_points=10, n_iter=30,)
print(optimizer.max)


#存储数据
time = []
n = 0
index = []
# 存储搜索到最好的十个配置
for key, value in optimizer.res[0]['params'].items():
    index.append(key)
# print (index)

data = pd.DataFrame(columns=[x for x in index])
data['runtime'] = ''
# print (data)
for i in optimizer.res:

    n = n + 1
    paramter = []
    execution = -i['target']
    for key, value in i['params'].items():
        paramter.append(value)
    paramter.append(execution)
    data.loc[n] = paramter
# print(data)
# data = data.sort_values('runtime').reset_index(drop=True)
# data = data[:5]
# data.insert(column='runtime',time)
data.to_csv(generation_confs, index=False)