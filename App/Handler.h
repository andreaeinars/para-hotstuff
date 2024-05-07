#ifndef HANDLER_H
#define HANDLER_H


#include <map>
#include <set>

#include "Message.h"
#include "Nodes.h"
#include "Log.h"
#include "Stats.h"
#include "user_types.h"

#include "TrustedFun.h"
#include "TrustedCh.h"

// Salticidae related stuff
#include <memory>
#include <cstdio>
#include <functional>
#include "salticidae/msg.h"
#include "salticidae/event.h"
#include "salticidae/network.h"
#include "salticidae/stream.h"

using std::placeholders::_1;
using std::placeholders::_2;


using PeerNet     = salticidae::PeerNetwork<uint8_t>;
using Peer        = std::tuple<PID,salticidae::PeerId>;
using Peers       = std::vector<Peer>;
using ClientNet   = salticidae::ClientNetwork<uint8_t>;
using MsgNet      = salticidae::MsgNetwork<uint8_t>;
using ClientNfo   = std::tuple<bool,unsigned int,unsigned int,ClientNet::conn_t>;
using Clients     = std::map<CID,ClientNfo>;
using rep_queue_t = salticidae::MPSCQueueEventDriven<std::pair<TID,CID>>;
using Time        = std::chrono::time_point<std::chrono::steady_clock>;


class Handler {

 private:
  PID myid;
  double timeout;                // timeout after which nodes start a new view
  unsigned int numFaults;        // number of faults
  unsigned int qsize;            // quorum size
  unsigned int total;            // total number of nodes
  Nodes nodes;                   // collection of the other nodes
  KEY priv;                      // private key
  View view = 0;                 // current view - initially 0
  unsigned int maxViews = 0;     // 0 means no constraints
  KeysFun kf;                    // To access crypto functions

  salticidae::EventContext pec; // peer ec
  salticidae::EventContext cec; // request ec
  PeerNet pnet;
  Peers peers;
  Clients clients;
  ClientNet cnet;
  std::thread c_thread; // request thread
  rep_queue_t rep_queue;
  salticidae::BoxObj<salticidae::ThreadCall> req_tcall;
  unsigned int viewsWithoutNewTrans = 0;
  bool started = false;
  bool stopped = false;
  salticidae::TimerEvent timer;
  View timerView; // view at which the timer was started

  std::list<Transaction> transactions; // current waiting to be processed
  std::map<View,Block> blocks; // blocks received in each view
  std::map<View,JBlock> jblocks; // blocks received in each view (Chained baseline)
  Log log; // log of messages

  void printClientInfo();

  void printNowTime(std::string msg);

  // returns the total number of nodes
  unsigned int getTotal();

  // returns the leader of view 'v'
  unsigned int getLeaderOf(View v);

  // returns the current leader
  unsigned int getCurrentLeader();

  // true iff 'myid' is the leader of view 'v'
  bool amLeaderOf(View v);

  // ture iff 'myid' is the leader of the current view
  bool amCurrentLeader();

  // used to print debugging info
  std::string nfo();

  bool timeToStop();
  void recordStats();
  void setTimer();

  bool Sverify(Signs signs, PID id, Nodes nodes, std::string s);

  Block createNewBlock(Hash hash);

  void replyTransactions(Transaction *transactions);
  void replyHash(Hash hash);

  // send messages
  void sendMsgNewView(MsgNewView msg, Peers recipients);
  void sendMsgPrepare(MsgPrepare msg, Peers recipients);
  void sendMsgLdrPrepare(MsgLdrPrepare msg, Peers recipients);
  void sendMsgPreCommit(MsgPreCommit msg, Peers recipients);
  void sendMsgCommit(MsgCommit msg, Peers recipients);

  void sendMsgNewViewCh(MsgNewViewCh msg, Peers recipients);
  void sendMsgPrepareCh(MsgPrepareCh msg, Peers recipients);
  void sendMsgLdrPrepareCh(MsgLdrPrepareCh msg, Peers recipients);

  // for leaders to start the phase where nodes will log prepare certificates
  void initiatePrepare(RData rdata);
  // for leaders to start the phase where nodes will log lock certificates
  void initiatePrecommit(RData rdata);
  // for leaders to start the phase where nodes execute
  void initiateCommit(RData rdata);

  bool verifyTransaction(MsgTransaction msg);
  bool verifyJust(Just just);

  // To start the code
  void getStarted();
  void prepare();

  void respondToProposal(Just justNv, Block b);
  void respondToPrepareJust(Just justPrep);
  void respondToPreCommitJust(Just justPc);

  Peers remove_from_peers(PID id);
  Peers keep_from_peers(PID id);

  void startNewViewOnTimeout();


  // ------------------------------------------------------------
  // Baseline
  // ------------------------------------------------------------

  void executeRData(RData rdata);
  void handleEarlierMessages();
  void startNewView();

  // Wrappers around the TEE functions
  Just callTEEsign();
  Just callTEEstore(Just j);
  Just callTEEprepare(Hash h, Just j);
  bool callTEEverify(Just j);

  void handleNewview(MsgNewView msg);
  void handlePrepare(MsgPrepare msg);
  void handleLdrPrepare(MsgLdrPrepare msg);
  void handlePrecommit(MsgPreCommit msg);
  void handleCommit(MsgCommit msg);
  void handleTransaction(MsgTransaction msg);

  void handle_newview(MsgNewView msg, const PeerNet::conn_t &conn);
  void handle_prepare(MsgPrepare msg, const PeerNet::conn_t &conn);
  void handle_ldrprepare(MsgLdrPrepare msg, const PeerNet::conn_t &conn);
  void handle_precommit(MsgPreCommit msg, const PeerNet::conn_t &conn);
  void handle_commit(MsgCommit msg, const PeerNet::conn_t &conn);
  void handle_transaction(MsgTransaction msg, const ClientNet::conn_t &conn);
  void handle_start(MsgStart msg, const ClientNet::conn_t &conn);

  // ------------------------------------------------------------
  // Chained HotStuff
  // ------------------------------------------------------------

  Just justNV;

  void startNewViewCh();

  Just callTEEsignCh();
  Just callTEEprepareCh(JBlock block, JBlock block0, JBlock block1);

  JBlock createNewBlockCh();

  Just ldrPrepareCh2just(MsgLdrPrepareCh msg);

  void tryExecuteCh(JBlock block, JBlock block0, JBlock block1);
  void voteCh(JBlock block);
  void prepareCh();
  void checkNewJustCh(RData data);
  void handleEarlierMessagesCh();

  void handleNewviewCh(MsgNewViewCh msg);
  void handlePrepareCh(MsgPrepareCh msg);
  void handleLdrPrepareCh(MsgLdrPrepareCh msg);

  void handle_newview_ch(MsgNewViewCh msg, const PeerNet::conn_t &conn);
  void handle_prepare_ch(MsgPrepareCh msg, const PeerNet::conn_t &conn);
  void handle_ldrprepare_ch(MsgLdrPrepareCh msg, const PeerNet::conn_t &conn);


 public:
  Handler(KeysFun kf, PID id, unsigned long int timeout, unsigned int constFactor, unsigned int numFaults, unsigned int maxViews, Nodes nodes, KEY priv, PeerNet::Config pconf, ClientNet::Config cconf);
};


#endif
