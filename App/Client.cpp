#include <stdio.h>
#include <sys/socket.h>
#include <stdlib.h>
#include <netinet/in.h>
#include <string.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <iostream>
#include <fstream>
#include <chrono>

#include "Message.h"

// Salticidae related stuff
#include "salticidae/msg.h"
#include "salticidae/event.h"
#include "salticidae/network.h"
#include "salticidae/stream.h"

using MsgNet    = salticidae::MsgNetwork<uint8_t>;
using Clock     = std::chrono::time_point<std::chrono::steady_clock>;
using TransInfo = std::tuple<unsigned int,Clock,Transaction>; // int: number of replies

const uint8_t MsgNewView::opcode;
const uint8_t MsgPrepare::opcode;
const uint8_t MsgLdrPrepare::opcode;
const uint8_t MsgPreCommit::opcode;
const uint8_t MsgCommit::opcode;

const uint8_t MsgNewViewCh::opcode;
const uint8_t MsgLdrPrepareCh::opcode;
const uint8_t MsgPrepareCh::opcode;

const uint8_t MsgNewViewPara::opcode;
const uint8_t MsgRecoverPara::opcode;
const uint8_t MsgLdrRecoverPara::opcode;
const uint8_t MsgVerifyPara::opcode;
const uint8_t MsgLdrPreparePara::opcode;
const uint8_t MsgPreparePara::opcode;
const uint8_t MsgPreCommitPara::opcode;
const uint8_t MsgCommitPara::opcode;

const uint8_t MsgTransaction::opcode;
const uint8_t MsgReply::opcode;
const uint8_t MsgStart::opcode;


salticidae::EventContext ec;
std::unique_ptr<MsgNet> net;          // network
std::map<PID,MsgNet::conn_t> conns;   // connections to the replicas
std::thread send_thread;              // thread to send messages
unsigned int qsize = 0;
unsigned int numNodes = 0;
unsigned int numFaults = 1;
unsigned int constFactor = 3;         // default value: by default, there are 3f+1 nodes
CID cid = 0;                          // id of this client
unsigned int numInstances = 1;        // by default clients wait for only 1 instance
std::map<TID,TransInfo> transactions; // current transactions
//std::map<TID,double> execTrans;       // set of executed transaction ids
std::map<TID, std::pair<std::chrono::steady_clock::time_point, std::chrono::steady_clock::time_point>> execTrans;

std::chrono::steady_clock::time_point when_last_reply = std::chrono::steady_clock::now();

unsigned int maxBlocks = 0;           // maximum number of blocks in a view
unsigned int sleepTime = 1;           // time the client sleeps between two sends (in microseconds)

Clock beginning;

unsigned int inst = 0; // instance number when repeating experiments

std::string statsThroughputLatency;
std::string debugThroughputLatency;

// In the chained versions, as we start with node 1 as the leader, we also send the first transaction to 1
#if defined(CHAINED_BASELINE)
bool skipFirst = true;
#else
bool skipFirst = false;
#endif

std::atomic<bool> running(true);


std::string cnfo() {
  return ("[C" + std::to_string(cid) + "]");
}

void send_start_to_all() {
  // TODO: sign
  Sign sign = Sign();
  MsgStart msg = MsgStart(cid,sign);
  std::cout << cnfo() << "sending start to all" << KNRM << std::endl;
  for (auto &p: conns) { net->send_msg(msg, p.second); }
}

unsigned int updTransaction(TID tid) {
  std::map<TID,TransInfo>::iterator it = transactions.find(tid);
  unsigned int numReplies = 0;
  if (it != transactions.end()) {
    TransInfo tup = it->second;
    numReplies = std::get<0>(tup)+1;
    transactions[tid]=std::make_tuple(numReplies,std::get<1>(tup),std::get<2>(tup));
  }
  return numReplies;
}

bool compare_double (const double& first, const double& second) { return (first < second); }

void printStats() {
  // auto end = std::chrono::steady_clock::now();
  // double time = std::chrono::duration_cast<std::chrono::microseconds>(end - beginning).count();
  // double secs = time / (1000*1000);
  // double kops = (numInstances * 1.0) / 1000;
  // double throughput = kops/secs;
  // std::cout << KMAG << cnfo() << "numInstances=" << numInstances << ";Kops=" << kops << ";secs=" << secs << KNRM << std::endl;

  std::chrono::steady_clock::time_point latestCompletionTime = beginning; // Initialize to the start time
  for (const auto& entry : execTrans) {
    if (entry.second.second > latestCompletionTime) {
      latestCompletionTime = entry.second.second;
    }
  }

  double totalDuration = std::chrono::duration_cast<std::chrono::microseconds>(latestCompletionTime - beginning).count();
  double secs = totalDuration / 1000000.0;
  double kops = (execTrans.size() * 1.0) / 1000.0;
  double throughput = kops / secs;

  std::cout << KMAG << cnfo() << "numInstances=" << execTrans.size() << "; Kops=" << kops << "; secs=" << secs << KNRM << std::endl;


  std::list<double> allLatencies;
  for (const auto& entry : execTrans) {
      double duration = std::chrono::duration_cast<std::chrono::microseconds>(entry.second.second - entry.second.first).count();
      double ms = duration / 1000.0; // Convert microseconds to milliseconds
      allLatencies.push_back(ms);
  }

  //double avgLatency = std::accumulate(allLatencies.begin(), allLatencies.end(), 0.0) / allLatencies.size();


  
  // we gather all latencies in a list
  // std::list<double> allLatencies;
  // for (std::map<TID,double>::iterator it = execTrans.begin(); it != execTrans.end(); ++it) {
  //  //if (DEBUGC) std::cout << KMAG << cnfo() << "tid=" << it->first << ";time=" << it->second << KNRM << std::endl;
  //   double ms = (it->second)/1000; /* latency in milliseconds */
  //   allLatencies.push_back(ms);
  // }

  double avg = 0.0;
  for (std::list<double>::iterator it = allLatencies.begin(); it != allLatencies.end(); ++it) {
    avg += (double)*it;
  }
  double latency = avg / allLatencies.size(); /* avg of milliseconds spent on a transaction */
  if (DEBUGC) std::cout << KMAG << cnfo() << "latency=" << latency << KNRM << std::endl;

  // double avg2 = 0.0;
  // for (std::list<double>::iterator it = allLatencies2.begin(); it != allLatencies2.end(); ++it) {
  //   avg2 += (double)*it;
  // }
  // double latency2 = avg2 / allLatencies2.size(); /* avg of milliseconds spent on a transaction */

  //End to end latency
  double endToEndLatency = (totalDuration / 1000) / numInstances;

  std::ofstream f(statsThroughputLatency);
  //f << std::to_string(throughput) << " " << std::to_string(latency);
  f << std::to_string(throughput) << " " << std::to_string(latency) << " " << std::to_string(allLatencies.size());
  f.close();

  if (DEBUGC) { std::cout << KMAG << cnfo() << "#before=" << execTrans.size() << ";#after=" << allLatencies.size() << KNRM << std::endl; }
}

void timeout_checker() {
    auto last_check = std::chrono::steady_clock::now();
    while (running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(1000)); // Check every second
        auto now = std::chrono::steady_clock::now();
        auto elapsed_time = std::chrono::duration_cast<std::chrono::seconds>(now - when_last_reply).count();
        if (elapsed_time > 15) {
            std::cout << "Timeout reached, not all responses received." << std::endl;
            printStats();  // Assume printStats function to display or log information
            send_thread.join();
            ec.stop();
            running = false;
            break;
        }
    }
}

// void executed(TID tid) {
//   std::map<TID,TransInfo>::iterator it = transactions.find(tid);
//   if (it != transactions.end()) {
//     TransInfo tup = it->second;
//     auto start = std::get<1>(tup);
//     auto end = std::chrono::steady_clock::now();
//     double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
//     execTrans[tid]=time;
//   }
// }
void executed(TID tid) {
    auto it = transactions.find(tid);
    if (it != transactions.end()) {
        TransInfo tup = it->second;
        auto start = std::get<1>(tup);
        auto end = std::chrono::steady_clock::now();
        execTrans[tid] = std::make_pair(start, end);
        // double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
        // execTrans2[tid]=time;
    }
}

void handle_reply(MsgReply &&msg, const MsgNet::conn_t &conn) {
  TID tid = msg.reply;
  //std::cout << cnfo() << "received reply for transaction " << tid << KNRM << std::endl;
  if (execTrans.find(tid) == execTrans.end()) { // the transaction hasn't been executed yet
    unsigned int numReplies = updTransaction(tid);
    if (DEBUGC) { std::cout << cnfo() << "received " << numReplies << "/" << qsize << " replies for transaction " << tid << KNRM << std::endl;}
    if (numReplies == qsize) {
      if (DEBUGC) { std::cout << cnfo() << "received all " << numReplies << " replies for transaction " << tid << KNRM << std::endl; }
      executed(tid);
      if (DEBUGC) { std::cout << cnfo() << "received:" << execTrans.size() << "/" << numInstances << KNRM << std::endl; }
      if (execTrans.size() == numInstances) {
        std::cout << cnfo() << "received replies for all " << numInstances << " transactions...stopping..." << KNRM << std::endl; 
        printStats();
        // Once we have received all the replies we want, we stop by:
        // (1) waiting for the sending thread to finish
        // (2) and by stopping the ec
        send_thread.join();
        ec.stop();
      }
    }
  }
  
  //auto time_now = std::chrono::steady_clock::now();
  // auto elapsed_time = std::chrono::duration_cast<std::chrono::seconds>(time_now - when_last_reply).count();
  when_last_reply = std::chrono::steady_clock::now(); // Update the last handled time

  // If the timeout period is reached and not all responses are received
  // if (elapsed_time > 20) {
  //     std::cout << "Timeout reached, not all responses received." << std::endl;
  //     printStats();  // Assume printStats function to display or log information
  //     send_thread.join();
  //     ec.stop();
  // }
}

void addNewTransaction(Transaction trans) {
  // 0 answers so far
  auto start = std::chrono::steady_clock::now();
  transactions[trans.getTid()]=std::make_tuple(0,start,trans);
}

MsgTransaction mkTransaction(TID transid) {
  Transaction transaction = Transaction(cid,transid,17);
  addNewTransaction(transaction);
  // TODO: sign
  Sign sign = Sign();
  MsgTransaction msg(transaction,sign);
  return msg;
}

void send_one_trans(MsgTransaction msg, MsgNet::conn_t conn) {
  net->send_msg(msg,conn);
}

unsigned int send_transactions_to_all(TID transid) {
  for (auto &p: conns) {
    if (DEBUGC) { std::cout << cnfo() << "sending transaction(" << transid << ") to " << p.first << KNRM << std::endl; }
    MsgTransaction msg = mkTransaction(transid);
    net->send_msg(msg, p.second);
    transid++;
  }
  return transid;
}

void send_transactions() {
  // The transaction id '0' is reserved for dummy transactions
  unsigned int transid = 1;
  beginning = std::chrono::steady_clock::now();
  while (transid <= numInstances) {
    for (auto &p: conns) {
      if (skipFirst) { skipFirst = false; }
      else {
        if (DEBUGC) { std::cout << cnfo() << "sending transaction(" << transid << ") to " << p.first << KNRM << std::endl; }
        MsgTransaction msg = mkTransaction(transid);
        net->send_msg(msg, p.second);
        usleep(sleepTime);
        if (DEBUGC) { std::cout << cnfo() << "slept for " << sleepTime << "; transid=" << transid << KNRM << std::endl; }
        transid++;
        if (transid > numInstances) { break; }
      }
    }
    // usleep(sleepTime);
    // if (DEBUGC) { std::cout << cnfo() << "slept for " << sleepTime << "; transid=" << transid << KNRM << std::endl; }
    // transid++;
    // if (transid > numInstances) { break; }
  }
  // auto timeout_duration = std::chrono::seconds(190);  // 90 seconds timeout
  // auto timeout_end_time = std::chrono::steady_clock::now() + timeout_duration;

  // // Loop to simulate processing and checking for timeout
  // while (std::chrono::steady_clock::now() < timeout_end_time) {
  //   // Simulate processing work or wait for replies
  //   std::this_thread::sleep_for(std::chrono::milliseconds(100));  // Sleep for 100 milliseconds
  // } 

  // // If the timeout period is reached and not all responses are received
  // if (std::chrono::steady_clock::now() >= timeout_end_time) {
  //     std::cout << "Timeout reached, not all responses received." << std::endl;
  //     printStats();  // Assume printStats function to display or log information
  //     send_thread.join();
  //     ec.stop();
  // }
}

int main(int argc, char const *argv[]) {
  KeysFun kf;

  if (argc > 1) { sscanf(argv[1], "%d", &cid); }
  std::cout << "[C-id=" << cid << "]" << KNRM << std::endl;

  if (argc > 2) { sscanf(argv[2], "%d", &numFaults); }
  std::cout << cnfo() << "#faults=" << numFaults << KNRM << std::endl;

  if (argc > 3) { sscanf(argv[3], "%d", &constFactor); }
  std::cout << cnfo() << "constFactor=" << constFactor << KNRM << std::endl;

  if (argc > 4) { sscanf(argv[4], "%d", &numInstances); }
  std::cout << cnfo() << "numInstances=" << numInstances << KNRM << std::endl;

  if (argc > 5) { sscanf(argv[5], "%d", &sleepTime); }
  std::cout << cnfo() << "sleepTime=" << sleepTime << KNRM << std::endl;

  if (argc > 6) { sscanf(argv[6], "%d", &inst); }
  std::cout << cnfo() << "instance=" << inst << KNRM << std::endl;

  if (argc > 7) { sscanf(argv[6], "%d", &maxBlocks); }
  std::cout << cnfo() << "maxBlocks=" << maxBlocks << KNRM << std::endl;

  numNodes = (constFactor*numFaults)+1;
  qsize = numNodes-numFaults;
  std::string confFile = "/app/config";
  Nodes nodes(confFile,numNodes);

  
  std::ifstream inFile(confFile);
  if (inFile.is_open()) {
        std::cout << "Successfully opened config file: " << confFile << std::endl;
        // Further processing here
        inFile.close();
    } else {
        std::cerr << "Failed to open config file: " << confFile << std::endl;
        // Handle the error, e.g., fallback, retry, or exit
  }



  // -- Stats
  auto timeNow = std::chrono::system_clock::now();
  std::time_t time = std::chrono::system_clock::to_time_t(timeNow);
  struct tm y2k = {0};
  double seconds = difftime(time,mktime(&y2k));
  std::string stamp = std::to_string(inst) + "-" + std::to_string(cid) + "-" + std::to_string(seconds);
  statsThroughputLatency = "/app/stats/client-throughput-latency-" + stamp;
  debugThroughputLatency = "/app/stats/debug-client-throughput-latency";

  // -- Public keys
  for (unsigned int i = 0; i < numNodes; i++) {
    //public key
    KEY pub;
    // Set public key - nothing special to do for EC
    #if defined(KK_RSA4096) || defined(KK_RSA2048)
        pub = RSA_new();
    #endif

    kf.loadPublicKey(i,&pub);
    if (DEBUGC) std::cout << KMAG << "node id: " << i << KNRM << std::endl;
    nodes.setPub(i,pub);
  }

  long unsigned int size = std::max({sizeof(MsgTransaction), sizeof(MsgReply), sizeof(MsgStart)});

  #if defined(BASIC_BASELINE)
  size = std::max({size,
                   sizeof(MsgNewView),
                   sizeof(MsgPrepare),
                   sizeof(MsgLdrPrepare),
                   sizeof(MsgPreCommit),
                   sizeof(MsgCommit)});
  #elif defined(CHAINED_BASELINE)
  size = std::max({size,
                   sizeof(MsgNewViewCh),
                   sizeof(MsgLdrPrepareCh),
                   sizeof(MsgPrepareCh)});
  #elif defined(PARALLEL_HOTSTUFF) 
  size = std::max({size,
                  sizeof(MsgNewViewPara),
                  sizeof(MsgPreparePara),
                  (sizeof(MsgRecoverPara) + maxBlocks * sizeof(PBlock)),
                  //sizeof(MsgRecoverPara),
                  sizeof(MsgLdrRecoverPara),
                  //sizeof(MsgVerifyPara),
                  (sizeof(MsgVerifyPara) + maxBlocks * sizeof(Hash)),
                  sizeof(MsgLdrPreparePara),
                  sizeof(MsgPreCommitPara),
                  sizeof(MsgCommitPara)});         
  #endif


  MsgNet::Config config;
  config.max_msg_size(size);
  net = std::make_unique<MsgNet>(ec,config);

  net->start();

  std::cout << cnfo() << "connecting..." << KNRM << std::endl;
  for (size_t j = 0; j < numNodes; j++) {
    NodeInfo* othernode = nodes.find(j);
    if (othernode != NULL) {
      std::cout << cnfo() << "connecting to " << j << KNRM << std::endl;
      salticidae::NetAddr peer_addr(othernode->getHost() + ":" + std::to_string(othernode->getCPort()));
      conns.insert(std::make_pair(j,net->connect_sync(peer_addr)));
    } else {
      std::cout << KLRED << cnfo() << "couldn't find " << j << "'s information among nodes" << KNRM << std::endl;
    }
  }

  net->reg_handler(handle_reply);

  send_start_to_all();
  send_thread = std::thread([]() { send_transactions(); });
  std::thread timeout_thread(timeout_checker);

  // check whether when_last is higher than 20 seconds in a loop

  // while (true) {
  //   auto time_now = std::chrono::steady_clock::now();
  //   auto elapsed_time = std::chrono::duration_cast<std::chrono::seconds>(time_now - when_last_reply).count();
  //   if (elapsed_time > 20) {
  //     std::cout << "Timeout reached, not all responses received." << std::endl;
  //     printStats();  // Assume printStats function to display or log information
  //     send_thread.join();
  //     ec.stop();
  //     break;
  //   }
  //   std::this_thread::sleep_for(std::chrono::milliseconds(300));
  // }

  auto shutdown = [&](int) {ec.stop();};
  salticidae::SigEvent ev_sigterm(ec, shutdown);
  ev_sigterm.add(SIGTERM);

  std::cout << cnfo() << "dispatch" << KNRM << std::endl;
  ec.dispatch();

  return 0;
}
