#ifndef HANDLER_H
#define HANDLER_H

#include <map>
#include <set>

#include "utils/Message.h"
#include "utils/Nodes.h"
#include "utils/Log.h"
#include "utils/Stats.h"
#include "utils/user_types.h"
#include "utils/TrustedFun.h"
#include "utils/TrustedCh.h"
#include "utils/TrustedPara.h"
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
  unsigned int localSeq = 1;     // local sequence number
  unsigned int maxViews = 4;     // 0 means no constraints
  KeysFun kf;                    // To access crypto functions
  static const unsigned int maxBlocksInView = 10;

  salticidae::EventContext pec; // peer ec
  salticidae::EventContext cec; // request ec
  PeerNet pnet;
  Peers peers;
  Clients clients;
  ClientNet cnet;
  std::thread c_thread; // request thread
  rep_queue_t rep_queue;
  unsigned int viewsWithoutNewTrans = 0;
  bool started = false;
  bool stopped = false;
  salticidae::TimerEvent timer;
  View timerView; // view at which the timer was started

  std::list<Transaction> transactions; // current waiting to be processed
  std::map<View,Block> blocks; // blocks received in each view
  std::map<View,JBlock> jblocks; // blocks received in each view (Chained baseline)

  // std::map<View, std::vector<PBlock>> pblocks;  //blocks received in each view (Parallel baseline)
  std::map<View, std::array<PBlock, maxBlocksInView>> pblocks;
  Log log; // log of messages

  // Because now there can be multiple justifications for multiple blocks
  std::set<std::pair<View, unsigned int>> initiatedPrepareCerts;
  std::set<std::pair<View, unsigned int>> initiatedPrecommitCerts ;
  std::set<std::pair<View, unsigned int>> initiatedCommitCerts;

  std::map<View, unsigned int> recoverResponses;

  unsigned int lastExecutedSeq = 0;

  Just justNV;
  std::string nfo(); // used to print debugging info

  Just verifiedJust; // just used for parallel

  // ------------------------------------------------------------
  // Common Protocol Functions
  // ------------------------------------------------------------

  void printClientInfo();
  void printNowTime(std::string msg);
  bool timeToStop();
  void recordStats();
  void setTimer();

  unsigned int getLeaderOf(View v); // returns the leader of view 'v'
  unsigned int getCurrentLeader(); // returns the current leader
  bool amLeaderOf(View v); // true iff 'myid' is the leader of view 'v'
  bool amCurrentLeader(); // ture iff 'myid' is the leader of the current view
  void getStarted(); // To start the code
  void handle_transaction(MsgTransaction msg, const ClientNet::conn_t &conn);
  void handle_start(MsgStart msg, const ClientNet::conn_t &conn);
  void startNewViewOnTimeout();
  bool verifyTransaction(MsgTransaction msg);
  Peers remove_from_peers(PID id);
  Peers keep_from_peers(PID id);
  bool Sverify(Signs signs, PID id, Nodes nodes, std::string s);
  bool verifyJust(Just just);
  bool verifyJustPara(Just just);
  void replyTransactions(Transaction *transactions);
  void replyHash(Hash hash);

  // ------------------------------------------------------------
  // Basic HotStuff
  // ------------------------------------------------------------
  void sendMsgNewView(MsgNewView msg, Peers recipients);
  void sendMsgPrepare(MsgPrepare msg, Peers recipients);
  void sendMsgLdrPrepare(MsgLdrPrepare msg, Peers recipients);
  void sendMsgPreCommit(MsgPreCommit msg, Peers recipients);
  void sendMsgCommit(MsgCommit msg, Peers recipients);

  Block createNewBlock(Hash hash);

  void prepare();
  void initiatePrepare(RData rdata); // for leaders to start the phase where nodes will log prepare certificates
  void initiatePrecommit(RData rdata); // for leaders to start the phase where nodes will log lock certificates
  void initiateCommit(RData rdata); // for leaders to start the phase where nodes execute

  void respondToProposal(Just justNv, Block b);
  void respondToPrepareJust(Just justPrep);
  void respondToPreCommitJust(Just justPc);

  // Wrappers around the TEE functions
  Just callTEEsign();
  Just callTEEstore(Just j);
  Just callTEEprepare(Hash h, Just j);

  void executeRData(RData rdata);
  void handleEarlierMessages();
  void startNewView();

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
  
  // ------------------------------------------------------------
  // Chained HotStuff
  // ------------------------------------------------------------

  void sendMsgNewViewCh(MsgNewViewCh msg, Peers recipients);
  void sendMsgPrepareCh(MsgPrepareCh msg, Peers recipients);
  void sendMsgLdrPrepareCh(MsgLdrPrepareCh msg, Peers recipients);

  JBlock createNewBlockCh();

  Just callTEEsignCh();
  Just callTEEprepareCh(JBlock block, JBlock block0, JBlock block1);
  Just ldrPrepareCh2just(MsgLdrPrepareCh msg);

  void startNewViewCh();
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

  // ------------------------------------------------------------
  // Parallel HotStuff
  // ------------------------------------------------------------
  void sendMsgNewViewPara(MsgNewViewPara msg, Peers recipients);
  void sendMsgRecoverPara(MsgRecoverPara msg, Peers recipients);
  void sendMsgLdrRecoverPara(MsgLdrRecoverPara msg, Peers recipients);
  void sendMsgPreparePara(MsgPreparePara msg, Peers recipients);
  void sendMsgVerifyPara(MsgVerifyPara msg, Peers recipients);
  void sendMsgLdrPreparePara(MsgLdrPreparePara msg, Peers recipients);
  void sendMsgPreCommitPara(MsgPreCommitPara msg, Peers recipients);
  void sendMsgCommitPara(MsgCommitPara msg, Peers recipients);

  PBlock createNewBlockPara(Hash hash);

  void executeRDataPara(RDataPara rdata);
  void executeBlocksFrom(View view, int startSeq, int endSeq);


  std::vector<unsigned int> getMissingSeqNumbersForJust(Just justNV);
  void initiateRecoverPara(std::vector<unsigned int> missing, Just just);
  // void initiateRecoverPara(RData rdata); // for leaders to start the phase where nodes will log prepare certificates
  void initiateVerifyPara(Just just); // for leaders to start the phase where nodes will log lock certificates
  void preparePara(Just just);
  void initiatePreparePara(RDataPara rdata); // for leaders to start the phase where nodes will log prepare certificates
  void initiatePrecommitPara(RDataPara rdata); // for leaders to start the phase where nodes will log lock certificates
  void initiateCommitPara(RDataPara rdata); // for leaders to start the phase where nodes execute

  void respondToVerifyJust(Just justPrep);
  void respondToProposalPara(Just justNv, PBlock b);
  void respondToPrepareJustPara(Just justPrep);
  void respondToPreCommitJustPara(Just justPc); 

  // AE-TODO is this necessary?
  Just callTEEsignPara();
  Just callTEEstorePara(Just j);
  Just callTEEpreparePara(PBlock block, Just j);
  Just callTEEVerifyPara(Just j, const std::vector<Hash> &blockHashes); 



  // void executeRDataPara(RData rdata);
  void handleEarlierMessagesPara();
  void startNewViewPara();

  void handleNewViewPara(MsgNewViewPara msg);
  void handleRecoverPara(MsgRecoverPara msg);
  void handleLdrRecoverPara(MsgLdrRecoverPara msg);
  void handleVerifyPara(MsgVerifyPara msg);
  void handlePreparePara(MsgPreparePara msg);
  void handleLdrPreparePara(MsgLdrPreparePara msg);
  void handlePrecommitPara(MsgPreCommitPara msg);
  void handleCommitPara(MsgCommitPara msg);

  void handle_newview_para(MsgNewViewPara msg, const PeerNet::conn_t &conn);
  void handle_recover_para(MsgRecoverPara msg, const PeerNet::conn_t &conn);
  void handle_ldrrecover_para(MsgLdrRecoverPara msg, const PeerNet::conn_t &conn);
  void handle_verify_para(MsgVerifyPara msg, const PeerNet::conn_t &conn);
  void handle_prepare_para(MsgPreparePara msg, const PeerNet::conn_t &conn);
  void handle_ldrprepare_para(MsgLdrPreparePara msg, const PeerNet::conn_t &conn);
  void handle_precommit_para(MsgPreCommitPara msg, const PeerNet::conn_t &conn);
  void handle_commit_para(MsgCommitPara msg, const PeerNet::conn_t &conn);

  void replyHashPara(Hash hash, unsigned int seq);

 public:
  Handler(KeysFun kf, PID id, unsigned long int timeout, unsigned int constFactor, unsigned int numFaults, unsigned int maxViews, Nodes nodes, KEY priv, PeerNet::Config pconf, ClientNet::Config cconf);
};


#endif
