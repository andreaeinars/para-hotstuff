from experpiments_params import *
from datetime import datetime
import subprocess
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter, LogLocator, MaxNLocator, AutoMinorLocator, NullFormatter,LogFormatter
import numpy as np
import os

colors = ['#3fa4d8', '#b2c324', '#ee657a', '#a363d9', '#fecc2f', '#db3838', '#f6621f', '#f9a227']
markers = ['o', 's', 'p', 'D', '^', 'v', '<', '>']
linestyles = ['-', '--', '-.', ':', '-', '--', '-.', ':']
labels = ['100 tx 0B', '100 tx, 128B','400 tx, 0B','400 tx, 128B','400 tx, 128B', '400 tx, 256B', ]
#labels = ['Normal','Byzantine']
#labels =['Byzantine']

showYlabel   = True
maxBlocksInView = [1,2,4,8,16,32,64,128]
faults = [1]
logScale = True

def createPlot(folderName, folder=False):
    def init_dicts():  # Dictionary initialization
        protocols = [f"PARALLEL_HOTSTUFF-{blocks}BLOCKS" for blocks in maxBlocksInView]
        print("protocols:", protocols)
        metrics = ["throughput-view", "latency-view", "handle", "crypto-sign", "crypto-verif"]
        return {protocol: {metric: {} for metric in metrics} for protocol in protocols}

    data_dict = init_dicts()

    global dockerCpu, dockerMem, networkLat, payloadSize, repeats, repeatsL2, numViews

    # Read parameters
    def parse_params(line):
        parts = line.split(" ")
        params = {part.split("=")[0]: part.split("=")[1].strip() for part in parts[1:]}
        global dockerCpu, dockerMem, networkLat, payloadSize, repeats, repeatsL2, numViews, networkLat, numTrans
        dockerCpu = float(params["cpus"])
        dockerMem = int(params["mem"])
        networkLat = int(params["lat"])
        payloadSize = int(params["payload"])
        repeats = int(params["repeats1"])
        repeatsL2 = int(params["repeats2"])
        numViews = int(params["views"])
        networkLat = int(params["netvar"])
        numTrans = int(params["numTrans"])

    def adjustFigAspect(fig, aspect=1):
        xsize, ysize = fig.get_size_inches()
        minsize = min(xsize, ysize)
        fig.set_size_inches(minsize * aspect, minsize * aspect, forward=True)

    # Update dictionaries with data points
    def update_dict(protocol, metric, blocksInView, pointVal):
        try:
            if metric not in data_dict[protocol]:
                return
            val, num = data_dict[protocol][metric].get(blocksInView, ([], 0))
            # Adjust scaling based on the original logic
            val.append(float(pointVal) if metric in ["throughput-view", "latency-view"] else float(pointVal) / numViews)

            data_dict[protocol][metric][blocksInView] = (val, num + 1)
        except Exception as e:
            pass

    if not folder:
        # Reading points from the file
        print("reading points from:", folderName)
        with open(folderName, 'r') as f:
            for line in f.readlines():
                if line.startswith("##params"):
                    parse_params(line)
                if line.startswith("protocol"):
                    parts = line.split(" ")
                    protocol = parts[0].split("=")[1]
                    try:
                        numBlocks = int(protocol.split('-')[-1].replace("BLOCKS", ""))
                    except:
                        numBlocks = 1
                    pointTag = parts[2].split("=")[0]
                    pointVal = float(parts[2].split("=")[1])
                    if pointVal < float('inf'):
                        update_dict(protocol, pointTag, numBlocks, pointVal)

    def dict2lists(d, quantileSize, sort=True):
        blocks, vals, nums = [], [], []
        for key, (val, num) in d.items():
            if not val:
                continue
            val = np.array(val)

            median = np.median(val)
            mad = np.median(np.abs(val - median))
            
            # Determine the outlier bounds
            lower_bound = median - 3 * mad
            upper_bound = median + 3 * mad
            
            # Filter out outliers
            filtered_val = [v for v in val if lower_bound <= v <= upper_bound]
         
            if not filtered_val:
                continue
    
            l = len(filtered_val)
            if quantileSize > 0:
                quantile_number = int((quantileSize / 100.0) * l)
                filtered_val = np.sort(filtered_val)[quantile_number:-quantile_number]
                m = len(filtered_val) 
            
            s = sum(filtered_val)
            v = s / m if m > 0 else 0.0
            blocks.append(key)
            vals.append(v)
            nums.append(m)
        if sort:
            sorted_tuples = sorted(zip(blocks, vals, nums))
            blocks, vals, nums = zip(*sorted_tuples) if sorted_tuples else (blocks, vals, nums)
        return blocks, vals, nums

    
    # Extracting data for plotting
    def extract_plot_data(metric):
        plot_data = {}
        for protocol in data_dict:
            print(f"Protocol: {data_dict[protocol][metric]}")
            blocks, vals, nums = dict2lists(data_dict[protocol][metric], 20, True)
            plot_data[protocol] = (blocks, vals, nums)
        return plot_data

    # Plotting data helper function
    def plot_data(ax, metric, ylabel, logScale, showYlabel, showLegend=True, showXlabel=False, color='blue', marker='o', linestyle='-', label=None):
        plot_data = extract_plot_data(metric)
        for protocol in plot_data:
            print(f"Protocol: {protocol}")
            print(f"Data: {plot_data[protocol]}")
        #sorted_protocols = sorted(plot_data.keys())
        sorted_protocols = sorted(plot_data.keys(), key=lambda p: int(p.split('-')[-1].replace('BLOCKS', '')))
        
        x_values = []
        y_values = []
        
        for protocol in sorted_protocols:
            data = plot_data[protocol]
            if data[0]:  # Only plot if there is data
                x_values.append(data[0][0])
                y_values.append(data[1][0])
                ax.plot(data[0], data[1], linewidth=LW, markersize=MS, color=color, marker=marker, linestyle=linestyle)

        print("Plotting protocol:", protocol)
        print("x_values:", x_values)
        if len(x_values) > 1:
            # Connect all points with a line
            ax.plot(x_values, y_values, linewidth=LW, markersize=MS, color=color, marker=marker, linestyle=linestyle, label=label)

        if showYlabel:
            ax.set(ylabel=ylabel)
        if showXlabel:
            ax.set(xlabel="Blocks in View")
        if logScale:
            ax.set_yscale('log')
        ax.set_xscale('log')
        if showLegend:
            ax.legend(fontsize='x-small')

        ax.set_xticks(maxBlocksInView)
        ax.set_xticklabels([str(x) for x in maxBlocksInView])

        print("ylabel:", ylabel)

        # To customize yticks

        # if "Throughput" in ylabel:
        #     print("Setting yticks for throughput")
        #     ticks = [20,40,100,200,400]
        #     ax.set_yticks(ticks)
        #     ax.get_yaxis().set_major_formatter(LogFormatter())
        #     ax.set_yticklabels([str(x) for x in ticks])

        # if "Latency" in ylabel:
        #     print("Setting yticks for lat")
        #     ticks = [1,3,10,20]
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
            title_info += f"\n(file={folderName}; cpus={dockerCpu}; mem={dockerMem}; lat={networkLat}; payload={payloadSize}; repeats1={repeats}; repeats2={repeatsL2}; #views={numViews}; regions=local; #trans={numTrans}; netvar={networkLat})"
        fig.suptitle(title_info)

    adjustFigAspect(fig, aspect=0.9)
    fig.set_figheight(6 if numPlots == 2 else 3)

    if folder:
        color_idx = 0
        def extract_timestamp(filename):
            timestamp_str = '-'.join(filename.split('-')[1:]).split('.')[0]
            return datetime.strptime(timestamp_str, '%d-%b-%Y-%H:%M:%S')

        # Get a sorted list of files based on timestamp
        files = sorted(os.listdir(folderName), key=extract_timestamp)
        # Iterate through all files in the specified folder
        for current_file in files:
            #dont process png files
            if current_file.endswith(".png"):
                continue
            print(f"current file: {current_file}")
            color = colors[color_idx%len(colors)]
            marker = markers[color_idx%len(markers)]
            linestyle = linestyles[color_idx%len(linestyles)]
            label = labels[color_idx%len(labels)]
            print("Label:", label)
            color_idx += 1
            #if current_file.endswith(".txt"):  # Adjust file extension if necessary
            data_dict = init_dicts()  # Reinitialize data_dict for each file
            pFile = os.path.join(folderName, current_file)
            print(f"reading points from: {pFile}")
            with open(pFile, 'r') as f:
                for line in f.readlines():
                    if line.startswith("##params"):
                        parse_params(line)
                    if line.startswith("protocol"):
                        parts = line.split(" ")
                        protocol = parts[0].split("=")[1]
                        numBlocks = int(protocol.split('-')[-1].replace("BLOCKS", ""))
                        pointTag = parts[2].split("=")[0]
                        pointVal = float(parts[2].split("=")[1])
                        if pointVal < float('inf'):
                            update_dict(protocol, pointTag, numBlocks, pointVal)

            if plotThroughput:
                plot_data(axs[0], "throughput-view", "Throughput (Kops/s)" if showYlabel else "", logScale, showYlabel=True, showLegend=True, color=color, marker=marker, linestyle=linestyle, label=label)
            if plotLatency:
                ax = axs[0] if numPlots == 1 else axs[1]
                ylabel = "Latency (ms)" if not plotHandle else "handling time (ms)"
                plot_data(ax, "latency-view", ylabel if showYlabel else "", logScale, showYlabel=True, showLegend=True, showXlabel=True,color=color, marker=marker, linestyle=linestyle)
        
    else:
        if plotThroughput:
            plot_data(axs[0], "throughput-view", "Throughput (Kops/s)" if showYlabel else "", logScale, showYlabel)

        if plotLatency:
            ax = axs[0] if numPlots == 1 else axs[1]
            ylabel = "Latency (ms)" if not plotHandle else "handling time (ms)"
            plot_data(ax, "latency-view", ylabel if showYlabel else "", logScale, showYlabel, showLegend=False, showXlabel=True )

    fig.savefig(plotFile, bbox_inches='tight', pad_inches=0.5)

    print("points are in", folder)
    print("plot is in", plotFile)
    if displayPlot:
        try:
            subprocess.call([displayApp, plotFile])
        except:
            print(f"couldn't display the plot using '{displayApp}'. Consider changing the 'displayApp' variable.")

    return {protocol: data_dict[protocol]["throughput-view"] for protocol in data_dict}

createPlot("cluster_stats/blocks-exp-3", folder=True)
