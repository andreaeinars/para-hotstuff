from experpiments_params import *
from datetime import datetime
import subprocess
from matplotlib import pyplot as plt
import os
import numpy as np
from matplotlib.ticker import FuncFormatter,LogLocator, ScalarFormatter, LogFormatter

maxBlocksInView = [1,4,8,16]
faults = [1,2,4,8,16]
logScale     = False

colors = ['#3fa4d8','#b2c324', '#ee657a','#a363d9', '#fecc2f', '#db3838', '#f6621f', '#f9a227']
#colors = ['#fecc2f','#ee657a', '#F6621F','#3fa4d8','#db3838','#b2c324']
#colors = ['#3fa4d8', '#b2c324', '#F6621F', '#a363d9', '#fecc2f', '#db3838', '#f6621f', '#f9a227']

#colors = ['#3fa4d8','#3fa4d8', '#b2c324','#b2c324', '#F6621F','#EE657A', '#f6621f', '#fecc2f', '#db3838', '#f6621f', '#f9a227']
#colors = ['#3FA4D8', '#3FC89A', '#2FA83A', '#EE657A', '#B657EE', '#9B57EE']

markers = ['s','o', 'p', 'D', '^', 'v', '<', '>']
#markers = ['s','p','p','p']
#markers = ['o','o', '^','^','s','s']
linestyles = ['-', '--', '-.', ':', '-', '--', '-.', ':']
#linestyles = ['-','-', '--','--','-.','-.']
#labels = ['Recover = 0', 'Recover, = 0.5', 'Recover = 1']
labels = ['No faults', '0.5f faults', 'f faults']
#'Chained 64B','Para 64B'
#labels = ['Normal, (4 Blocks)','Normal' ,'Byz, Timeout=4 (4 Blocks) ','Byzantine (Timeout=4)','Byz, Timeout=1 (4 Blocks)','Byzantine (Timeout=1)','Byz to=3 4B','Byz to=3 16B','Byz to=4 4B','Byz to=4 16B']
#labels = ['Byz to=5 4B','Byz to=5 16B','Byz to=2 4B','Byz to=2 16B','Byz to=3 ,4B','Byz to=3 16B','Byz to=4 4B','Byz to=4 16B']
#labels = ['Chained 0B', 'Para 0B','Chained 128B','Para 128B','Chained 256B','Para 256B' ]
#labels = ['Chained HS', 'Para HS, Recover = 0','Para HS, Recover = 0.5','Para HS, Recover = 1']
colors_crash = ['#3fa4d8', '#b2c324']

protocol_styles = {
    "BASIC_BASELINE": {'marker': 'o', 'linestyle': '-', 'color': '#3fa4d8'},
    "CHAINED_BASELINE": {'marker': 's', 'linestyle': '--', 'color': '#b2c324'},
    "PARALLEL_HOTSTUFF-1BLOCKS": {'marker': 'p', 'linestyle': '-.', 'color': '#ee657a'},
    "PARALLEL_HOTSTUFF-2BLOCKS": {'marker': 'D', 'linestyle': '-.', 'color': '#a363d9'},
    "PARALLEL_HOTSTUFF-4BLOCKS": {'marker': '^', 'linestyle': ':', 'color': '#fecc2f'},
    "PARALLEL_HOTSTUFF-8BLOCKS": {'marker': 'v', 'linestyle': '-', 'color': '#db3838'},
    "PARALLEL_HOTSTUFF-16BLOCKS": {'marker': '<', 'linestyle': '--', 'color': '#f6621f'},
    "PARALLEL_HOTSTUFF-32BLOCKS": {'marker': '>', 'linestyle': '-.', 'color': '#f9a227'},
}

legend_labels = {
    "BASIC_BASELINE": "Basic HS",
    "CHAINED_BASELINE": "Chained HS",
    "PARALLEL_HOTSTUFF-1BLOCKS": "Para-HS (1 Block)",
    "PARALLEL_HOTSTUFF-2BLOCKS": "Para-HS (2 Blocks)",
    "PARALLEL_HOTSTUFF-4BLOCKS": "Para-HS (4 Blocks)",
    "PARALLEL_HOTSTUFF-8BLOCKS": "Para-HS (8 Blocks)",
    "PARALLEL_HOTSTUFF-16BLOCKS": "Para-HS (16 Blocks)",
    "PARALLEL_HOTSTUFF-32BLOCKS": "Para-HS (32 Blocks)",
}


def createPlot(pFile, folder=False):
    data_dict = {}

    global dockerCpu, dockerMem, networkLat, payloadSize, repeats, repeatsL2, numViews

    # Read parameters
    def parse_params(line):
        parts = line.split(" ")
        params = {part.split("=")[0]: part.split("=")[1].strip() for part in parts[1:]}
        global dockerCpu, dockerMem, networkLat, payloadSize, repeats, repeatsL2, numViews, numTrans #,networkVar 
        dockerCpu = float(params["cpus"])
        dockerMem = int(params["mem"])
        networkLat = int(params["lat"])
        payloadSize = int(params["payload"])
        repeats = int(params["repeats1"])
        repeatsL2 = int(params["repeats2"])
        numViews = int(params["views"])
        #networkLat = int(params["netvar"])
        #numTrans = int(params["numTrans"])

    def adjustFigAspect(fig, aspect=1):
        xsize, ysize = fig.get_size_inches()
        minsize = min(xsize, ysize)
        fig.set_size_inches(minsize * aspect, minsize * aspect, forward=True)

    def update_dict(protocol, metric, numFaults, pointVal, unique_key):
        if folder:
            key = f"{protocol}_{unique_key}"
        else:
            key = protocol
        if key not in data_dict:
            data_dict[key] = {m: {} for m in ["throughput-view", "latency-view", "handle", "crypto-sign", "crypto-verif"]}
        if metric not in data_dict[key]:
            return
        val, num = data_dict[key][metric].get(numFaults, ([], 0))
        val.append(float(pointVal) if metric in ["throughput-view", "latency-view"] else float(pointVal) / numViews)
        data_dict[key][metric][numFaults] = (val, num + 1)

    def read_file(file_path, file_index):
        print("reading points from:", file_path)
        with open(file_path, 'r') as f:
            for line in f.readlines():
                if line.startswith("##params"):
                    parse_params(line)
                if line.startswith("protocol"):
                    parts = line.split(" ")
                    protocol = parts[0].split("=")[1]
                    numFaults = int(parts[1].split("=")[1])
                    pointTag = parts[2].split("=")[0]
                    pointVal = float(parts[2].split("=")[1])
                    if pointVal < float('inf'):
                        update_dict(protocol, pointTag, numFaults, pointVal, file_index)

    if folder:
        def extract_timestamp(filename):
            timestamp_str = '-'.join(filename.split('-')[1:]).split('.')[0]
            return datetime.strptime(timestamp_str, '%d-%b-%Y-%H:%M:%S')

        # Get a sorted list of files based on timestamp
        files = sorted(os.listdir(pFile), key=extract_timestamp)
        for i, filename in enumerate(files):
            if filename.endswith(".png"):
                continue
            file_path = os.path.join(pFile, filename)
            if os.path.isfile(file_path):
                read_file(file_path, i)
    else:
        read_file(pFile, 0)

    # Function to convert dictionaries to lists
    def dict2lists(d, quantileSize, sort=True):
        faults, vals, nums = [], [], []
        
        for key, (val, num) in d.items():
            faults.append(key)
            val = sorted(val)
            l = len(val)

            if quantileSize > 0:
                n = int(l * quantileSize / 100 / 2)  # Divide by 2 to account for both ends
                newval = val[n:l-n]  # Trim quantileSize% from each end
            else:
                newval = val 

            m = len(newval)
            if m > 0:
                s = sum(newval)
                v = s / m
            else:
                v = 0.0  # Avoid division by zero if no data is left after filtering

            vals.append(v)
            nums.append(m)
        if sort:
            sorted_tuples = sorted(zip(faults, vals, nums))
            #faults, vals, nums = zip(*sorted_tuples)
            faults, vals, nums = zip(*sorted_tuples) if sorted_tuples else (faults, vals, nums)
        return faults, vals, nums
    
    # Extracting data for plotting
    def extract_plot_data(metric):
        plot_data = {}
        for protocol in data_dict:
            #print(f"DATA: {data_dict[protocol][metric]}")
            faults, vals, nums = dict2lists(data_dict[protocol][metric], 20, True)
            plot_data[protocol] = (faults, vals, nums)
        return plot_data

    # Plotting data helper function
    def plot_data(ax, metric, ylabel, logScale, showYlabel, showLegend=True, showXlabel=False):
        plot_data = extract_plot_data(metric)

        for i, (protocol, data) in enumerate(plot_data.items()):
            if data[0]:  # Only plot if there is data
                if folder:
                    style = {
                        'color': colors[i % len(colors)],
                        'marker': markers[i % len(markers)],
                        'linestyle': linestyles[i % len(linestyles)]
                    }
                    label = labels[i % len(labels)]
                else:
                    style = protocol_styles.get(protocol, {'marker': 'o', 'linestyle': linestyles[i % len(linestyles)], 'color': colors[i % len(colors)]})
                    label = legend_labels.get(protocol, protocol)

                ax.plot(data[0], data[1], linewidth=LW, marker=style['marker'], markersize=MS, color=style['color'], linestyle=style['linestyle'], label=label)

        if showYlabel:
            ax.set(ylabel=ylabel)
        if showXlabel:
            ax.set(xlabel="Number of faults")

        if logScale:
            ax.set_yscale('log')
            ax.yaxis.set_major_locator(LogLocator(base=10, numticks=4))
        if showLegend:
            ax.legend(fontsize='x-small')

        # To customize the y-axis ticks

        # if ylabel == "throughput (Kops/s)":
        #     ticks = [1,3,10,12]
        #     ax.set_yticks(ticks)
        #     ax.get_yaxis().set_major_formatter(LogFormatter())
        #     ax.set_yticklabels([str(x) for x in ticks])

    # Plotting setup
    LW = 1  # linewidth
    MS = 5  # markersize
    XYT = (0, 5)
    numPlots = 2 if plotThroughput and plotLatency else 1
    fig, axs = plt.subplots(numPlots, 1, figsize=(10, 6))
    axs = [axs] if numPlots == 1 else axs

    if showTitle:
        title_info = "Throughputs (top) & Latencies (bottom)" if not plotHandle else "Handling time"
        if debugPlot:
            title_info += f"\n(file={pFile}; cpus={dockerCpu}; mem={dockerMem}; lat={networkLat}; payload={payloadSize}; repeats1={repeats}; repeats2={repeatsL2}; #views={numViews}; regions=local; #trans={numTrans}; netvar={networkLat})"
        fig.suptitle(title_info)

    adjustFigAspect(fig, aspect=0.9)
    fig.set_figheight(6 if numPlots == 2 else 3)

    if plotThroughput:
        plot_data(axs[0], "throughput-view", "throughput (Kops/s)", logScale, showYlabel)

    if plotLatency:
        ax = axs[0] if numPlots == 1 else axs[1]
        ylabel = "latency (ms)" if not plotHandle else "handling time (ms)"
        plot_data(ax, "latency-view", ylabel, logScale, showYlabel, showLegend=False, showXlabel=True )

    fig.savefig(plotFile, bbox_inches='tight', pad_inches=0.5)
    print("points are in", pFile)
    print("plot is in", plotFile)
    if displayPlot:
        try:
            subprocess.call([displayApp, plotFile])
        except:
            print(f"couldn't display the plot using '{displayApp}'. Consider changing the 'displayApp' variable.")

    return {protocol: data_dict[protocol]["throughput-view"] for protocol in data_dict}


createPlot("cluster_stats/control-exp-faults-128pl/points-15-Jun-2024-23:19:06.437124", folder = False)