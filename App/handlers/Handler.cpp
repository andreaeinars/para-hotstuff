#include <fstream>
#include "Handler.h"

std::mutex mu_trans;
Time startTime = std::chrono::steady_clock::now();
Time startView = std::chrono::steady_clock::now();
std::string statsVals;             // Throuput + latency + handle + crypto
std::string statsDone;             // done recording the stats
Time curTime;
Stats stats;                   // To collect statistics
std::string Handler::nfo() { return "[" + std::to_string(this->myid) + "]"; }

TrustedFun tf;
TrustedCh tp; // 'p' for pipelined

// ------------------------------------------------------------
// Message Opcodes
// ------------------------------------------------------------

//#if defined(BASIC_BASELINE)
const uint8_t MsgNewView::opcode;
const uint8_t MsgLdrPrepare::opcode;
const uint8_t MsgPrepare::opcode;
const uint8_t MsgPreCommit::opcode;
const uint8_t MsgCommit::opcode;
//#elif defined(CHAINED_BASELINE)
const uint8_t MsgNewViewCh::opcode;
const uint8_t MsgLdrPrepareCh::opcode;
const uint8_t MsgPrepareCh::opcode;
//#endif

const uint8_t MsgTransaction::opcode;
const uint8_t MsgReply::opcode;
const uint8_t MsgStart::opcode;

Handler::Handler(KeysFun k, PID id, unsigned long int timeout, unsigned int constFactor, unsigned int numFaults, unsigned int maxViews, Nodes nodes, KEY priv, PeerNet::Config pconf, ClientNet::Config cconf) :
pnet(pec,pconf), cnet(cec,cconf) {
  this->myid         = id;
  this->timeout      = timeout;
  this->numFaults    = numFaults;
  this->total        = (constFactor*this->numFaults)+1;
  this->qsize        = this->total-this->numFaults;
  this->nodes        = nodes;
  this->priv         = priv;
  this->maxViews     = maxViews;
  this->kf           = k;

  if (DEBUG1) { std::cout << KBLU << nfo() << "starting handler" << KNRM << std::endl; }
  if (DEBUG1) { std::cout << KBLU << nfo() << "qsize=" << this->qsize << KNRM << std::endl; }

  // Trusted Functions
  tf = TrustedFun(this->myid,this->priv,this->qsize);
  tp = TrustedCh(this->myid,this->priv,this->qsize);

  // -- Salticidae
  // the client event context handles replies through the 'rep_queue' queue
  rep_queue.reg_handler(cec, [this](rep_queue_t &q) {
                               std::pair<TID,CID> p;
                               while (q.try_dequeue(p)) {
                                 TID tid = p.first;
                                 CID cid = p.second;
                                 Clients::iterator cit = this->clients.find(cid);
                                 if (cit != this->clients.end()) {
                                   ClientNfo cnfo = cit->second;
                                   MsgReply reply(tid);
                                   ClientNet::conn_t recipient = std::get<3>(cnfo);
                                   if (DEBUG1) std::cout << KBLU << nfo() << "sending reply to " << cid << ":" << reply.prettyPrint() << KNRM << std::endl;
                                   try {
                                     this->cnet.send_msg(reply,recipient);
                                     (this->clients)[cid]=std::make_tuple(std::get<0>(cnfo),std::get<1>(cnfo),std::get<2>(cnfo)+1,std::get<3>(cnfo));
                                   } catch(std::exception &err) {
                                     if (DEBUG0) { std::cout << KBLU << nfo() << "couldn't send reply to " << cid << ":" << reply.prettyPrint() << "; " << err.what() << KNRM << std::endl; }
                                   }
                                 } else {
                                   if (DEBUG0) { std::cout << KBLU << nfo() << "couldn't reply to unknown client: " << cid << KNRM << std::endl; }
                                 }
                               }
                               return false;
                             });

  this->timer = salticidae::TimerEvent(pec, [this](salticidae::TimerEvent &) {
                                              if (DEBUG0) std::cout << KMAG << nfo() << "timer ran out" << KNRM << std::endl;
                                              startNewViewOnTimeout();
                                              this->timer.del();
                                              this->timer.add(this->timeout);
                                            });

  HOST host = "127.0.0.1";
  PORT rport = 8760 + this->myid;
  PORT cport = 9760 + this->myid;

  NodeInfo* ownnode = nodes.find(this->myid);
  if (ownnode != NULL) {
    host  = ownnode->getHost();
    rport = ownnode->getRPort();
    cport = ownnode->getCPort();
  } else {
    std::cout << KLRED << nfo() << "couldn't find own information among nodes" << KNRM << std::endl;
  }

  salticidae::NetAddr paddr = salticidae::NetAddr(host + ":" + std::to_string(rport));
  this->pnet.start();
  this->pnet.listen(paddr);

  salticidae::NetAddr caddr = salticidae::NetAddr(host + ":" + std::to_string(cport));
  this->cnet.start();
  this->cnet.listen(caddr);

  if (DEBUG1) { std::cout << KBLU << nfo() << "connecting..." << KNRM << std::endl; }
  for (size_t j = 0; j < this->total; j++) {
    if (this->myid != j) {
      NodeInfo* othernode = nodes.find(j);
      if (othernode != NULL) {
        salticidae::NetAddr peer_addr(othernode->getHost() + ":" + std::to_string(othernode->getRPort()));
        salticidae::PeerId other{peer_addr};
        this->pnet.add_peer(other);
        this->pnet.set_peer_addr(other, peer_addr);
        this->pnet.conn_peer(other);
        if (DEBUG1) { std::cout << KBLU << nfo() << "added peer:" << j << KNRM << std::endl; }
        this->peers.push_back(std::make_pair(j,other));
      } else {
        std::cout << KLRED << nfo() << "couldn't find " << j << "'s information among nodes" << KNRM << std::endl;
      }
    }
  }

  #if defined(BASIC_BASELINE)
    this->pnet.reg_handler(salticidae::generic_bind(&Handler::handle_newview,    this, _1, _2));
    this->pnet.reg_handler(salticidae::generic_bind(&Handler::handle_prepare,    this, _1, _2));
    this->pnet.reg_handler(salticidae::generic_bind(&Handler::handle_ldrprepare, this, _1, _2));
    this->pnet.reg_handler(salticidae::generic_bind(&Handler::handle_precommit,  this, _1, _2));
    this->pnet.reg_handler(salticidae::generic_bind(&Handler::handle_commit,     this, _1, _2));
  #elif defined(CHAINED_BASELINE)
    this->pnet.reg_handler(salticidae::generic_bind(&Handler::handle_newview_ch,    this, _1, _2));
    this->pnet.reg_handler(salticidae::generic_bind(&Handler::handle_prepare_ch,    this, _1, _2));
    this->pnet.reg_handler(salticidae::generic_bind(&Handler::handle_ldrprepare_ch, this, _1, _2));
  #endif

  this->cnet.reg_handler(salticidae::generic_bind(&Handler::handle_transaction, this, _1, _2));
  this->cnet.reg_handler(salticidae::generic_bind(&Handler::handle_start, this, _1, _2));

  // Stats
  auto timeNow = std::chrono::system_clock::now();
  std::time_t time = std::chrono::system_clock::to_time_t(timeNow);
  struct tm y2k = {0};
  double seconds = difftime(time,mktime(&y2k));
  statsVals = "stats/vals-" + std::to_string(this->myid) + "-" + std::to_string(seconds);
  statsDone = "stats/done-" + std::to_string(this->myid) + "-" + std::to_string(seconds);
  stats.setId(this->myid);

  auto pshutdown = [&](int) {pec.stop();};
  salticidae::SigEvent pev_sigterm(pec, pshutdown);
  pev_sigterm.add(SIGTERM);

  auto cshutdown = [&](int) {cec.stop();};
  salticidae::SigEvent cev_sigterm(cec, cshutdown);
  cev_sigterm.add(SIGTERM);

  c_thread = std::thread([this]() { cec.dispatch(); });

  if (DEBUG0) { std::cout << KBLU << nfo() << "dispatching" << KNRM << std::endl; }
  pec.dispatch();
}

// ------------------------------------------------------------
// Common Protocol Functions
// ------------------------------------------------------------

Hash getHash(hash_t *h) { // loads a Hash from [h]
  return Hash(h->set,h->hash);
}

RData getRData (rdata_t *d) {
  Hash   proph = getHash(&(d->proph));
  View   propv = d->propv;
  Hash   justh = getHash(&(d->justh));
  View   justv = d->justv;
  Phase1 phase = (Phase1)d->phase;
  RData  data(proph,propv,justh,justv,phase);
  return data;
}

Just getJust(just_t *j) { // loads a Just from [j]
  RData rdata = getRData(&(j->rdata));
  Sign  a[MAX_NUM_SIGNATURES];
  for (int i = 0; i < MAX_NUM_SIGNATURES; i++) {
    a[i]=Sign(j->signs.signs[i].set,j->signs.signs[i].signer,j->signs.signs[i].sign);
  }
  Signs signs(j->signs.size,a);
  return Just((bool)j->set,rdata,signs);
}

void Handler::printClientInfo() {
  for (Clients::iterator it = this->clients.begin(); it != this->clients.end(); it++) {
    CID cid = it->first;
    ClientNfo cnfo = it->second;
    bool running = std::get<0>(cnfo);
    unsigned int received = std::get<1>(cnfo);
    unsigned int replied = std::get<2>(cnfo);
    ClientNet::conn_t conn = std::get<3>(cnfo);
    if (DEBUG0) { std::cout << KRED << nfo() << "CLIENT[id=" << cid << ",running=" << running << ",#received=" << received << ",#replied=" << replied << "]" << KNRM << std::endl; }
  }
}

void Handler::printNowTime(std::string msg) {
  auto now = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(now - startView).count();
  double etime = (stats.getTotalViewTime(0).tot + time) / (1000*1000);
  std::cout << KBLU << nfo() << msg << " @ " << etime << KNRM << std::endl;
}

bool Handler::timeToStop() {
  bool b = this->maxViews > 0 && this->maxViews <= this->view+1;
  if (DEBUG) { std::cout << KBLU << nfo() << "timeToStop=" << b << ";maxViews=" << this->maxViews << ";viewsWithoutNewTrans=" << this->viewsWithoutNewTrans << ";pending-transactions=" << this->transactions.size() << KNRM << std::endl; }
  if (DEBUG1) { if (b) { std::cout << KBLU << nfo() << "maxViews=" << this->maxViews << ";viewsWithoutNewTrans=" << this->viewsWithoutNewTrans << ";pending-transactions=" << this->transactions.size() << KNRM << std::endl; } }
  return b;
}

void Handler::recordStats() {
  if (DEBUG1) std::cout << KLGRN << nfo() << "DONE - printing stats" << KNRM << std::endl;

  // *** TODO: MAKE THIS A PARAMETER ***
  unsigned int quant1 = 0;
  unsigned int quant2 = 10;

  // Throughput
  Times totv = stats.getTotalViewTime(quant2);
  double kopsv = ((totv.n)*(MAX_NUM_TRANSACTIONS)*1.0) / 1000;
  double secsView = /*time*/ totv.tot / (1000*1000);
  if (DEBUG0) std::cout << KBLU << nfo() << "VIEW|view=" << this->view << ";Kops=" << kopsv << ";secs=" << secsView << ";n=" << totv.n << KNRM << std::endl;
  double throughputView = kopsv/secsView;

  // Debugging - handle
  Times toth = stats.getTotalHandleTime(quant1);
  double kopsh = ((toth.n)*(MAX_NUM_TRANSACTIONS)*1.0) / 1000;
  double secsHandle = /*time*/ toth.tot / (1000*1000);
  if (DEBUG0) std::cout << KBLU << nfo() << "HANDLE|view=" << this->view << ";Kops=" << kopsh << ";secs=" << secsHandle << ";n=" << toth.n << KNRM << std::endl;
  // Latency

  #if defined (CHAINED_BASELINE)
    double latencyView = (stats.getExecTimeAvg() / 1000)/* milli-seconds spent on views */;
  #else
    double latencyView = (totv.tot/totv.n / 1000)/* milli-seconds spent on views */;
  #endif
  
  // Handle
  double handle = (toth.tot / 1000); /* milli-seconds spent on handling messages */

  // Crypto
  double ctimeS  = stats.getCryptoSignTime();
  double cryptoS = (ctimeS / 1000); /* milli-seconds spent on crypto */
  double ctimeV  = stats.getCryptoVerifTime();
  double cryptoV = (ctimeV / 1000); /* milli-seconds spent on crypto */

  std::ofstream fileVals(statsVals);
  fileVals << std::to_string(throughputView)
           << " " << std::to_string(latencyView)
           << " " << std::to_string(handle)
           << " " << std::to_string(stats.getCryptoSignNum())
           << " " << std::to_string(cryptoS)
           << " " << std::to_string(stats.getCryptoVerifNum())
           << " " << std::to_string(cryptoV);
  fileVals.close();

  // Done
  std::ofstream fileDone(statsDone);
  fileDone.close();
  if (DEBUG1) std::cout << KBLU << nfo() << "printing 'done' file: " << statsDone << KNRM << std::endl;
}

void Handler::setTimer() { // reset the timer, and record the current view
  this->timer.del();
  this->timer.add(this->timeout);
  this->timerView = this->view;
}

unsigned int Handler::getLeaderOf(View v) { return (v % this->total); }

unsigned int Handler::getCurrentLeader() { return getLeaderOf(this->view); }

bool Handler::amLeaderOf(View v) { return (this->myid == getLeaderOf(v)); }

bool Handler::amCurrentLeader() { return (this->myid == getCurrentLeader()); }

void Handler::getStarted() {
  startTime = std::chrono::steady_clock::now();
  startView = std::chrono::steady_clock::now();

  PID leader = getCurrentLeader();
  Peers recipients = keep_from_peers(leader);
  PID nextLeader = getLeaderOf(this->view+1);
  Peers nextRecipients = keep_from_peers(nextLeader);

  #if defined(BASIC_BASELINE)
    Just j = callTEEsign();
    if (DEBUG1) std::cout << KBLU << nfo() << "initial just:" << j.prettyPrint() << KNRM << std::endl;
    MsgNewView msg(j.getRData(),j.getSigns());
    if (DEBUG1) std::cout << KBLU << nfo() << "starting with:" << msg.prettyPrint() << KNRM << std::endl;
    if (amCurrentLeader()) { handleNewview(msg); }
    else { sendMsgNewView(msg,recipients); } // Send new-view to the leader of the current view
    if (DEBUG) std::cout << KBLU << nfo() << "sent new-view to leader(" << leader << ")" << KNRM << std::endl;
  #elif defined(CHAINED_BASELINE)
    // We start voting
    Just j = callTEEsignCh();
    if (DEBUG1) std::cout << KBLU << nfo() << "initial just:" << j.prettyPrint() << KNRM << std::endl;
    MsgNewViewCh msg(j.getRData(),j.getSigns().get(0));
    if (DEBUG1) std::cout << KBLU << nfo() << "starting with:" << msg.prettyPrint() << KNRM << std::endl;
    this->view = 1; // The view starts at 1 here
    this->jblocks[0] = JBlock(); // we store the genesis block at view 0
    stats.startExecTime(0,std::chrono::steady_clock::now());
    // We handle the message
    if (amCurrentLeader()) { handleNewviewCh(msg); }
    else {
      sendMsgNewViewCh(msg,nextRecipients);
      handleEarlierMessagesCh();
    }
    if (DEBUG) std::cout << KBLU << nfo() << "sent new-view to leader(" << nextLeader << ")" << KNRM << std::endl;
  #endif
}

void Handler::handle_transaction(MsgTransaction msg, const ClientNet::conn_t &conn) {
  handleTransaction(msg);
}

void Handler::handle_start(MsgStart msg, const ClientNet::conn_t &conn) {
  CID cid = msg.cid;

  if (this->clients.find(cid) == this->clients.end()) {
    (this->clients)[cid]=std::make_tuple(true,0,0,conn);
  }

  if (!this->started) {
    this->started=true;
    getStarted();
  }
}

void Handler::startNewViewOnTimeout() {
  // TODO: start a new-view
#if defined(BASIC_BASELINE)
  if (DEBUG0) std::cout << KMAG << nfo() << "starting a new view" << KNRM << std::endl;
  startNewView();
#elif defined (CHAINED_BASELINE)
  startNewViewCh();
#endif
}

bool Handler::verifyTransaction(MsgTransaction msg) { return true; /*msg.verify(this->nodes);*/ }

std::string recipients2string(Peers recipients) {
  std::string s;
  for (Peers::iterator it = recipients.begin(); it != recipients.end(); ++it) {
    Peer peer = *it;
    s += std::to_string(std::get<0>(peer)) + ";";
  }
  return s;
}

Peers Handler::remove_from_peers(PID id) {
  Peers ret;
  for (Peers::iterator it = this->peers.begin(); it != this->peers.end(); ++it) {
    Peer peer = *it;
    if (id != std::get<0>(peer)) { ret.push_back(peer); }
  }
  return ret;
}

Peers Handler::keep_from_peers(PID id) {
  Peers ret;
  for (Peers::iterator it = this->peers.begin(); it != this->peers.end(); ++it) {
    Peer peer = *it;
    if (id == std::get<0>(peer)) { ret.push_back(peer); }
  }
  return ret;
}

std::vector<salticidae::PeerId> getPeerids(Peers recipients) {
  std::vector<salticidae::PeerId> ret;
  for (Peers::iterator it = recipients.begin(); it != recipients.end(); ++it) {
    Peer peer = *it;
    ret.push_back(std::get<1>(peer));
  }
  return ret;
}

bool Handler::Sverify(Signs signs, PID id, Nodes nodes, std::string s) {
  bool b = signs.verify(stats, id, nodes, s);
  return b;
}

bool Handler::verifyJust(Just just) {
  return Sverify(just.getSigns(),this->myid,this->nodes,just.getRData().toString());
}

void Handler::replyTransactions(Transaction *transactions) { // send replies corresponding to 'hash'
  for (int i = 0; i < MAX_NUM_TRANSACTIONS; i++) {
    Transaction trans = transactions[i];
    CID cid = trans.getCid();
    TID tid = trans.getTid();
    // The transaction id '0' is reserved for dummy transactions
    if (tid != 0) {
      Clients::iterator cit = this->clients.find(cid);
      if (cit != this->clients.end()) {
        rep_queue.enqueue(std::make_pair(tid,cid));
        if (DEBUG1) std::cout << KBLU << nfo() << "sending reply to " << cid << ":" << tid << KNRM << std::endl;
      } else {
        if (DEBUG0) { std::cout << KBLU << nfo() << "unknown client: " << cid << KNRM << std::endl; }
      }
    }
  }
}

void Handler::replyHash(Hash hash) { // send replies corresponding to 'hash'
  std::map<View,Block>::iterator it = this->blocks.find(this->view);
  if (it != this->blocks.end()) {
    Block block = (Block)it->second;
    if (block.hash() == hash) {
      if (DEBUG1) std::cout << KBLU << nfo() << "found block for view=" << this->view << ":" << block.prettyPrint() << KNRM << std::endl;
      replyTransactions(block.getTransactions());
    } else {
      if (DEBUG1) std::cout << KBLU << nfo() << "recorded block but incorrect hash for view " << this->view << KNRM << std::endl;
      if (DEBUG1) std::cout << KBLU << nfo() << "checking hash:" << hash.toString() << KNRM << std::endl;
    }
  } else {
    if (DEBUG1) std::cout << KBLU << nfo() << "no block recorded for view " << this->view << KNRM << std::endl;
  }
}

// ------------------------------------------------------------
// Basic HotStuff
// ------------------------------------------------------------

void Handler::sendMsgNewView(MsgNewView msg, Peers recipients) {
  if (DEBUG1) std::cout << KBLU << nfo() << "sending:" << msg.prettyPrint() << "->" << recipients2string(recipients) << KNRM << std::endl;
  this->pnet.multicast_msg(msg, getPeerids(recipients));
}

void Handler::sendMsgPrepare(MsgPrepare msg, Peers recipients) {
  if (DEBUG1) std::cout << KBLU << nfo() << "sending:" << msg.prettyPrint() << "->" << recipients2string(recipients) << KNRM << std::endl;
  this->pnet.multicast_msg(msg, getPeerids(recipients));
  if (DEBUGT) printNowTime("sending MsgPrepare");
}

void Handler::sendMsgLdrPrepare(MsgLdrPrepare msg, Peers recipients) {
  if (DEBUG1) std::cout << KBLU << nfo() << "sending(" << sizeof(msg) << "-" << sizeof(MsgLdrPrepare) << "):" << msg.prettyPrint() << "->" << recipients2string(recipients) << KNRM << std::endl;
  this->pnet.multicast_msg(msg, getPeerids(recipients));
  if (DEBUGT) printNowTime("sending MsgLdrPrepare");
}

void Handler::sendMsgPreCommit(MsgPreCommit msg, Peers recipients) {
  if (DEBUG1) std::cout << KBLU << nfo() << "sending:" << msg.prettyPrint() << "->" << recipients2string(recipients) << KNRM << std::endl;
  this->pnet.multicast_msg(msg, getPeerids(recipients));
  if (DEBUGT) printNowTime("sending MsgPreCommit");
}

void Handler::sendMsgCommit(MsgCommit msg, Peers recipients) {
  if (DEBUG1) std::cout << KBLU << nfo() << "sending:" << msg.prettyPrint() << "->" << recipients2string(recipients) << KNRM << std::endl;
  this->pnet.multicast_msg(msg, getPeerids(recipients));
  if (DEBUGT) printNowTime("sending MsgCommit");
}


Block Handler::createNewBlock(Hash hash) {
  std::lock_guard<std::mutex> guard(mu_trans);
  Transaction trans[MAX_NUM_TRANSACTIONS];
  int i = 0;

  // We fill the block we have with transactions we have received so far
  while (i < MAX_NUM_TRANSACTIONS && !this->transactions.empty()) {
    trans[i]=this->transactions.front();
    this->transactions.pop_front();
    i++;
  }

  if (DEBUG1) { std::cout << KGRN << nfo() << "filled block with " << i << " transactions" << KNRM << std::endl; }
  unsigned int size = i;

  while (i < MAX_NUM_TRANSACTIONS) { // we fill the rest with dummy transactions
    trans[i]=Transaction();
    i++;
  }
  return Block(hash,size,trans);
}


void Handler::prepare() { // For leader to do begin a view (prepare phase)
  auto start = std::chrono::steady_clock::now();
  // We first create a block that extends the highest prepared block
  Just justNV = this->log.findHighestNv(this->view);
  Block block = createNewBlock(justNV.getRData().getJusth());

  // We create our own justification for that block
  Just justPrep = callTEEprepare(block.hash(),justNV);
  if (justPrep.isSet()) {
    if (DEBUG1) std::cout << KBLU << nfo() << "storing block for view=" << this->view << ":" << block.prettyPrint() << KNRM << std::endl;
    this->blocks[this->view]=block;

    // We create a message out of that commitment, which we'll store in our log
    Signs signs = justPrep.getSigns();
    MsgPrepare msgPrep(justPrep.getRData(),signs);

    // We now create a proposal out of that block to send out to the other replicas
    Proposal prop(justNV,block);

    // We send this proposal in a prepare message
    MsgLdrPrepare msgProp(prop,signs);
    Peers recipients = remove_from_peers(this->myid);
    sendMsgLdrPrepare(msgProp,recipients);
    if (DEBUG) std::cout << KBLU << nfo() << "sent prepare (" << msgProp.prettyPrint() << ") to backups" << KNRM << std::endl;

    // We store our own proposal in the log
    if (this->qsize <= this->log.storePrep(msgPrep)) {
      initiatePrepare(justPrep.getRData());
    }
  } else {
    if (DEBUG2) std::cout << KBLU << nfo() << "bad justification" << justPrep.prettyPrint() << KNRM << std::endl;
  }
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTotalPrepTime(time);
}

void Handler::initiatePrepare(RData rdata) { // For leaders to forward prepare justifications to all nodes
  Signs signs = (this->log).getPrepare(rdata.getPropv(),this->qsize);
  if (DEBUG) std::cout << KBLU << nfo() << "prepare signatures: " << signs.prettyPrint() << KNRM << std::endl;
  // We should not need to check the size of 'signs' as this function should only be called, when this is possible
  if (signs.getSize() == this->qsize) {
    MsgPrepare msgPrep(rdata,signs);
    Peers recipients = remove_from_peers(this->myid);
    sendMsgPrepare(msgPrep,recipients);
    if (DEBUG) std::cout << KBLU << nfo() << "sent prepare certificate to backups (" << msgPrep.prettyPrint() << ")" << KNRM << std::endl;

    // The leader also stores the prepare message
    Just justPc = callTEEstore(Just(rdata,signs));
    MsgPreCommit msgPc(justPc.getRData(),justPc.getSigns());

    // We store our own pre-commit in the log
    if (this->qsize <= this->log.storePc(msgPc)) { 
      initiatePrecommit(justPc.getRData());
    }
  }
}

void Handler::initiatePrecommit(RData rdata) { // For leaders to generate a pre-commit with f+1 signatures
  Signs signs = (this->log).getPrecommit(rdata.getPropv(),this->qsize);
  // We should not need to check the size of 'signs' as this function should only be called, when this is possible
  if (signs.getSize() == this->qsize) {
    MsgPreCommit msgPc(rdata,signs);
    Peers recipients = remove_from_peers(this->myid);
    sendMsgPreCommit(msgPc,recipients);
    if (DEBUG) std::cout << KBLU << nfo() << "sent pre-commit to backups (" << msgPc.prettyPrint() << ")" << KNRM << std::endl;

    // The leader also stores the prepare message
    Just justCom = callTEEstore(Just(rdata,signs));
    MsgCommit msgCom(justCom.getRData(),justCom.getSigns());

    // We store our own commit in the log
    if (this->qsize <= this->log.storeCom(msgCom)) {
      initiateCommit(justCom.getRData());
    }
  }
}

void Handler::initiateCommit(RData rdata) { // For leaders to generate a commit with f+1 signatures
  Signs signs = (this->log).getCommit(rdata.getPropv(),this->qsize);
  // We should not need to check the size of 'signs' as this function should only be called, when this is possible
  if (signs.getSize() == this->qsize) {
    MsgCommit msgCom(rdata,signs);
    Peers recipients = remove_from_peers(this->myid);
    sendMsgCommit(msgCom,recipients);
    if (DEBUG) std::cout << KBLU << nfo() << "sent commit certificate to backups (" << msgCom.prettyPrint() << ")" << KNRM << std::endl;

    executeRData(rdata); // We can now execute the block:
  }
}

void Handler::respondToProposal(Just justNv, Block block) {
  // We create our own justification for that block
  Just newJustPrep = callTEEprepare(block.hash(),justNv);
  if (newJustPrep.isSet()) {
    if (DEBUG1) std::cout << KBLU << nfo() << "storing block for view=" << this->view << ":" << block.prettyPrint() << KNRM << std::endl;
    this->blocks[this->view]=block;
    // We create a message out of that commitment, which we'll store in our log
    MsgPrepare msgPrep(newJustPrep.getRData(),newJustPrep.getSigns());
    Peers recipients = keep_from_peers(getCurrentLeader());
    sendMsgPrepare(msgPrep,recipients);
  } else {
    if (DEBUG2) std::cout << KBLU << nfo() << "bad justification" << newJustPrep.prettyPrint() << KNRM << std::endl;
  }
}

void Handler::respondToPrepareJust(Just justPrep) { // For backups to respond to prepare certificates received from the leader
  Just justPc = callTEEstore(justPrep);
  MsgPreCommit msgPc(justPc.getRData(),justPc.getSigns());
  Peers recipients = keep_from_peers(getCurrentLeader());
  sendMsgPreCommit(msgPc,recipients);
  if (DEBUG) std::cout << KBLU << nfo() << "sent pre-commit (" << msgPc.prettyPrint() << ") to leader" << KNRM << std::endl;
}

void Handler::respondToPreCommitJust(Just justPc) { // For backups to respond to pre-commit certificates received from the leader
  Just justCom = callTEEstore(justPc);
  MsgCommit msgCom(justCom.getRData(),justCom.getSigns());
  Peers recipients = keep_from_peers(getCurrentLeader());
  sendMsgCommit(msgCom,recipients);
  if (DEBUG) std::cout << KBLU << nfo() << "sent commit (" << msgCom.prettyPrint() << ") to leader" << KNRM << std::endl;
}


Just Handler::callTEEsign() {
  auto start = std::chrono::steady_clock::now();
  Just just = tf.TEEsign(stats);
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTEEsign(time);
  stats.addTEEtime(time);
  return just;
}

Just Handler::callTEEprepare(Hash h, Just j) {
  auto start = std::chrono::steady_clock::now();
  Just just = tf.TEEprepare(stats,this->nodes,h,j);
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTEEprepare(time);
  stats.addTEEtime(time);
  return just;
}

Just Handler::callTEEstore(Just j) {
  auto start = std::chrono::steady_clock::now();
  Just just = tf.TEEstore(stats,this->nodes,j);
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTEEstore(time);
  stats.addTEEtime(time);
  return just;
}


void Handler::executeRData(RData rdata) {
  auto endView = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(endView - startView).count();
  startView = endView;
  stats.incExecViews();
  stats.addTotalViewTime(time);
  if (this->transactions.empty()) { this->viewsWithoutNewTrans++; } else { this->viewsWithoutNewTrans = 0; }

  // Execute
  // TODO: We should wait until we received the block corresponding to the hash to execute
  if (DEBUG0 && DEBUGE) std::cout << KRED << nfo() << "R-EXECUTE(" << this->view << "/" << this->maxViews << ":" << time << ")" << stats.toString() << KNRM << std::endl;
  replyHash(rdata.getProph());

  if (timeToStop()) {
    recordStats();
  } else {
    startNewView();
  }
}

void Handler::handleEarlierMessages() {
  // *** THIS IS FOR LATE NODES TO PRO-ACTIVELY PROCESS MESSAGES THEY HAVE ALREADY RECEIVED FOR THE NEW VIEW ***
  // We now check whether we already have enough information to start the next view if we're the leader
  if (amCurrentLeader()) {
    Signs signsNV = this->log.getNewView(this->view,this->qsize);
    if (signsNV.getSize() == this->qsize) { // we have enough new view messages to start the new view
      prepare();
    }
  } else {
    // First we check whether the view has already been locked
    // (i.e., we received a pre-commit certificate from the leader),
    // in which case we don't need to go through the previous steps.
    Signs signsPc = (this->log).getPrecommit(this->view,this->qsize);
    if (signsPc.getSize() == this->qsize) {
      if (DEBUG1) std::cout << KMAG << nfo() << "catching up using pre-commit certificate" << KNRM << std::endl;
      Just justPc = this->log.firstPrecommit(this->view);
      callTEEsign();  // We skip the prepare phase (this is otherwise a TEEprepare):
      callTEEsign(); // We skip the pre-commit phase (this is otherwise a TEEstore):
      respondToPreCommitJust(justPc); // We store the pre-commit certificate
      Signs signsCom = (this->log).getCommit(this->view,this->qsize);
      if (signsCom.getSize() == this->qsize) {
        Just justCom = this->log.firstCommit(this->view);
        executeRData(justCom.getRData());
      }
    } else { // We don't have enough pre-commit signatures
      // TODO: we could still have enough commit signatures, in which case we might want to skip to that phase
      Signs signsPrep = (this->log).getPrepare(this->view,this->qsize);
      if (signsPrep.getSize() == this->qsize) {
        if (DEBUG1) std::cout << KMAG << nfo() << "catching up using prepare certificate" << KNRM << std::endl;
        // TODO: If we're late, we currently store two prepare messages (in the prepare phase,
        // the one from the leader with 1 sig; and in the pre-commit phase, the one with f+1 sigs.
        Just justPrep = this->log.firstPrepare(this->view);
        callTEEsign(); // We skip the prepare phase (this is otherwise a TEEprepare): 
        respondToPrepareJust(justPrep); // We store the prepare certificate
      } else {
        MsgLdrPrepare msgProp = this->log.firstProposal(this->view);
        if (msgProp.signs.getSize() == 1) { // If we've stored the leader's proposal
          if (DEBUG1) std::cout << KMAG << nfo() << "catching up using leader proposal" << KNRM << std::endl;
          Proposal prop = msgProp.prop;
          respondToProposal(prop.getJust(),prop.getBlock());
        }
      }
    }
  }
}

void Handler::startNewView() { // TODO: also trigger new-views when there is a timeout
  Just just = callTEEsign();
  while (just.getRData().getPropv() <= this->view) { just = callTEEsign(); } // generate justifications until we can generate one for the next view
  this->view++; // increment the view -> THE NODE HAS NOW MOVED TO THE NEW-VIEW
  setTimer(); // We start the timer

  // if the lastest justification we've generated is for what is now the current view (since we just incremented it)
  // and round 0, then send a new-view message
  if (just.getRData().getPropv() == this->view && just.getRData().getPhase() == PH1_NEWVIEW) {
    MsgNewView msg(just.getRData(),just.getSigns());
    if (amCurrentLeader()) {
      handleEarlierMessages();
      handleNewview(msg);
    }
    else {
      PID leader = getCurrentLeader();
      Peers recipients = keep_from_peers(leader);
      sendMsgNewView(msg,recipients);
      handleEarlierMessages();
    }
  } else {
    // Something wrong happened
  }
}

void Handler::handleTransaction(MsgTransaction msg) {
  std::lock_guard<std::mutex> guard(mu_trans);
  auto start = std::chrono::steady_clock::now();
  if (DEBUG1) std::cout << KBLU << nfo() << "handling:" << msg.prettyPrint() << KNRM << std::endl;
  if (verifyTransaction(msg)) {
    Transaction trans = msg.trans;
    CID cid = trans.getCid();
    Clients::iterator it = this->clients.find(cid);
    if (it != this->clients.end()) { // we found an entry for 'cid'
      ClientNfo cnfo = (ClientNfo)(it->second);
      bool running = std::get<0>(cnfo);
      if (running) {
        // We got a new transaction from a live client
        if ((this->transactions).size() < (this->transactions).max_size()) {
          if (DEBUG1) { std::cout << KBLU << nfo() << "pushing transaction:" << trans.prettyPrint() << KNRM << std::endl; }
          (this->clients)[cid]=std::make_tuple(true,std::get<1>(cnfo)+1,std::get<2>(cnfo),std::get<3>(cnfo));
          this->transactions.push_back(trans);
        } else { if (DEBUG0) { std::cout << KMAG << nfo() << "too many transactions (" << (this->transactions).size() << "/" << (this->transactions).max_size() << "), transaction rejected from client: " << cid << KNRM << std::endl; } }
      } else { if (DEBUG0) { std::cout << KMAG << nfo() << "transaction rejected from stopped client: " << cid << KNRM << std::endl; } }
    } else { if (DEBUG0) { std::cout << KMAG << nfo() << "transaction rejected from unknown client: " << cid << KNRM << std::endl; } }
  } else { if (DEBUG1) std::cout << KMAG << nfo() << "discarded:" << msg.prettyPrint() << KNRM << std::endl; }
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTotalHandleTime(time);
}

void Handler::handleNewview(MsgNewView msg) {
  // NEW-VIEW messages are received by leaders
  // Once a leader has received f+1 new-view messages, it creates a proposal out of the highest prepared block
  // and sends this proposal in a PREPARE message
  auto start = std::chrono::steady_clock::now();
  if (DEBUG1) std::cout << KBLU << nfo() << "handling:" << msg.prettyPrint() << KNRM << std::endl;
  Hash   hashP = msg.rdata.getProph();
  View   viewP = msg.rdata.getPropv();
  Phase1 ph    = msg.rdata.getPhase();
  if (hashP.isDummy() && viewP >= this->view && ph == PH1_NEWVIEW && amLeaderOf(viewP)) {
    if (this->log.storeNv(msg) == this->qsize && viewP == this->view) {
      prepare();
    }
  } else {
    if (DEBUG1) std::cout << KMAG << nfo() << "discarded:" << msg.prettyPrint() << KNRM << std::endl;
  }
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTotalHandleTime(time);
  stats.addTotalNvTime(time);
}

void Handler::handle_newview(MsgNewView msg, const PeerNet::conn_t &conn) {
  handleNewview(msg);
}

void Handler::handleLdrPrepare(MsgLdrPrepare msg) { // This is only for backups
  auto start = std::chrono::steady_clock::now();
  if (DEBUG1) std::cout << KBLU << nfo() << "handling:" << msg.prettyPrint() << KNRM << std::endl;
  Proposal prop = msg.prop;
  Just justNV = prop.getJust();
  RData rdataNV = justNV.getRData();
  Block b = prop.getBlock();

  // We re-construct the justification generated by the leader
  RData rdataLdrPrep(b.hash(),rdataNV.getPropv(),rdataNV.getJusth(),rdataNV.getJustv(),PH1_PREPARE);
  Just ldrJustPrep(rdataLdrPrep,msg.signs);
  bool vm = verifyJust(ldrJustPrep);

  if (rdataNV.getPropv() >= this->view
      && vm
      && b.extends(rdataNV.getJusth())) {
    if (rdataNV.getPropv() == this->view) { // If the message is for the current view we act upon it right away
      respondToProposal(justNV,b);
    } else{ // If the message is for later, we store it
      if (DEBUG1) std::cout << KMAG << nfo() << "storing:" << msg.prettyPrint() << KNRM << std::endl;
      this->log.storeProp(msg);
    }
  }
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTotalHandleTime(time);
  if (DEBUGT) std::cout << KMAG << nfo() << "MsgLdrPrepare3:" << time << KNRM << std::endl;
}

void Handler::handle_ldrprepare(MsgLdrPrepare msg, const PeerNet::conn_t &conn) {
  if (DEBUGT) printNowTime("handling MsgLdrPrepare");
  handleLdrPrepare(msg);
}

void Handler::handlePrepare(MsgPrepare msg) { // This is for both for the leader and backups
  auto start = std::chrono::steady_clock::now();
  if (DEBUG1) std::cout << KBLU << nfo() << "handling:" << msg.prettyPrint() << KNRM << std::endl;
  RData rdata = msg.rdata;
  Signs signs = msg.signs;
  if (rdata.getPropv() == this->view) {
    if (amCurrentLeader()) { // As a leader, we wait for f+1 proposals before we calling TEEpropose
      if (this->log.storePrep(msg) == this->qsize) {
        initiatePrepare(rdata);
      }
    } else { // As a replica, if we receive a prepare message with f+1 signatures, then we pre-commit
      if (signs.getSize() == this->qsize) {
        respondToPrepareJust(Just(rdata,signs));
      }
    }
  } else {
    if (DEBUG1) std::cout << KMAG << nfo() << "storing:" << msg.prettyPrint() << KNRM << std::endl;
    if (rdata.getPropv() > this->view) { this->log.storePrep(msg); }
  }
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTotalHandleTime(time);
}

void Handler::handle_prepare(MsgPrepare msg, const PeerNet::conn_t &conn) {
  handlePrepare(msg);
}

void Handler::handlePrecommit(MsgPreCommit msg) {
  auto start = std::chrono::steady_clock::now();
  if (DEBUG1) std::cout << KBLU << nfo() << "handling:" << msg.prettyPrint() << KNRM << std::endl;
  RData  rdata = msg.rdata;
  Signs  signs = msg.signs;
  View   propv = rdata.getPropv();
  Phase1 phase = rdata.getPhase();
  if (propv == this->view && phase == PH1_PRECOMMIT) {
    if (amCurrentLeader()) { // As a leader, we wait for f+1 pre-commits before we combine the messages
      if (this->log.storePc(msg) == this->qsize) {
        // Bundle the pre-commits together and send them to the backups
        initiatePrecommit(rdata);
      }
    } else { // As a backup:
      if (signs.getSize() == this->qsize) {
        respondToPreCommitJust(Just(rdata,signs));
      }
    }
  } else {
    if (rdata.getPropv() > this->view) {
      if (DEBUG1) std::cout << KMAG << nfo() << "storing:" << msg.prettyPrint() << KNRM << std::endl;
      this->log.storePc(msg);
      // TODO: we'll have to check whether we have this information later
    }
  }
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTotalHandleTime(time);
}

void Handler::handle_precommit(MsgPreCommit msg, const PeerNet::conn_t &conn) {
  handlePrecommit(msg);
}

void Handler::handleCommit(MsgCommit msg) {
  auto start = std::chrono::steady_clock::now();
  if (DEBUG1) std::cout << KBLU << nfo() << "handling:" << msg.prettyPrint() << KNRM << std::endl;
  RData  rdata = msg.rdata;
  Signs  signs = msg.signs;
  View   propv = rdata.getPropv();
  Phase1 phase = rdata.getPhase();
  if (propv == this->view && phase == PH1_COMMIT) {
    if (amCurrentLeader()) { // As a leader, we wait for f+1 commits before we combine the messages
      if (this->log.storeCom(msg) == this->qsize) {
        initiateCommit(rdata);
      }
    } else { // As a backup:
      if (signs.getSize() == this->qsize && verifyJust(Just(rdata,signs))) {
        executeRData(rdata);
      }
    }
  } else {
    if (DEBUG1) std::cout << KMAG << nfo() << "discarded:" << msg.prettyPrint() << KNRM << std::endl;
    if (propv > this->view) {
      if (amLeaderOf(propv)) { // If we're the leader of that later view, we log the message
        // We don't need to verify it as the verification will be done inside the TEE
        this->log.storeCom(msg);
      } else { // If we're not the leader, we only store it, if we can verify it
        if (verifyJust(Just(rdata,signs))) { this->log.storeCom(msg); }
      }
      // TODO: we'll have to check whether we have this information later
    }
  }
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTotalHandleTime(time);
}

void Handler::handle_commit(MsgCommit msg, const PeerNet::conn_t &conn) {
  handleCommit(msg);
}


// ------------------------------------------------------------
// Chained HotStuff
// ------------------------------------------------------------

void Handler::sendMsgNewViewCh(MsgNewViewCh msg, Peers recipients) {
  if (DEBUG1) std::cout << KBLU << nfo() << "sending:" << msg.prettyPrint() << "->" << recipients2string(recipients) << KNRM << std::endl;
  this->pnet.multicast_msg(msg, getPeerids(recipients));
}

void Handler::sendMsgPrepareCh(MsgPrepareCh msg, Peers recipients) {
  if (DEBUG1) std::cout << KBLU << nfo() << "sending:" << msg.prettyPrint() << "->" << recipients2string(recipients) << KNRM << std::endl;
  this->pnet.multicast_msg(msg, getPeerids(recipients));
  if (DEBUGT) printNowTime("sending MsgPrepareCh");
}

void Handler::sendMsgLdrPrepareCh(MsgLdrPrepareCh msg, Peers recipients) {
  if (DEBUG1) std::cout << KBLU << nfo() << "sending(" << sizeof(msg) << "-" << sizeof(MsgLdrPrepareCh) << "):" << msg.prettyPrint() << "->" << recipients2string(recipients) << KNRM << std::endl;
  this->pnet.multicast_msg(msg, getPeerids(recipients));
  if (DEBUGT) printNowTime("sending MsgLdrPrepareCh");
}


JBlock Handler::createNewBlockCh() {
  // The justification will have a view this->view-1 if things went well,
  // and otherwise there will be a gap between just's view and this->view (capturing blank blocks)
  std::lock_guard<std::mutex> guard(mu_trans);

  Transaction trans[MAX_NUM_TRANSACTIONS];
  int i = 0;
  // We fill the block we have with transactions we have received so far
  while (i < MAX_NUM_TRANSACTIONS && !this->transactions.empty()) {
    trans[i]=this->transactions.front();
    this->transactions.pop_front();
    i++;
  }

  if (DEBUG1) { std::cout << KGRN << nfo() << "filled block with " << i << " transactions" << KNRM << std::endl; }

  unsigned int size = i;
  // we fill the rest with dummy transactions
  while (i < MAX_NUM_TRANSACTIONS) {
    trans[i]=Transaction();
    i++;
  }
  return JBlock(this->view,this->justNV,size,trans);
}


Just Handler::callTEEsignCh() {
  auto start = std::chrono::steady_clock::now();
  Just just = tp.TEEsign();
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTEEsign(time);
  stats.addTEEtime(time);
  return just;
}

Just Handler::callTEEprepareCh(JBlock block, JBlock block0, JBlock block1) {
  auto start = std::chrono::steady_clock::now();
  Just just = tp.TEEprepare(stats,this->nodes,block,block0,block1);
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTEEprepare(time);
  stats.addTEEtime(time);
  return just;
}

Just Handler::ldrPrepareCh2just(MsgLdrPrepareCh msg) { // For backups to verify MsgLdrPrepareCh messages send by leaders
  JBlock block = msg.block;
  RData rdata(block.hash(),block.getView(),Hash(),View(),PH1_PREPARE);
  Signs signs = Signs(msg.sign);
  return Just(rdata,signs);
}

void Handler::startNewViewCh() {
  Just justNv = callTEEsignCh();
  // generate justifications until we can generate one for the next view
  while (justNv.getRData().getPropv() < this->view || justNv.getRData().getPhase() != PH1_NEWVIEW) {
    if (DEBUG1) std::cout << KMAG << nfo() << "generaring yet a new-view:" << this->view << ":" << justNv.prettyPrint() << KNRM << std::endl;
    justNv = callTEEsignCh();
  }

  if (justNv.getSigns().getSize() == 1) {

    PID nextLeader = getLeaderOf(this->view+1);
    Peers recipientsNL = keep_from_peers(nextLeader);
    Sign sigNv = justNv.getSigns().get(0);
    MsgNewViewCh msgNv(justNv.getRData(),sigNv);

    if (amLeaderOf(this->view+1)) { this->log.storeNvCh(msgNv); } // If we're the leader of the next view, we store the message
    else { sendMsgNewViewCh(msgNv,recipientsNL); } // Otherwise we send it
    
    this->view++; // increment the view
    setTimer(); // start the timer

    if (!amLeaderOf(this->view)) {
      handleEarlierMessagesCh(); // try to handler earlier messages
    }
  }
}

void Handler::tryExecuteCh(JBlock block, JBlock block0, JBlock block1) {
  // TODO: execute also all blocks that come before that haven't been executed yet
  // we skip this step if block0 is the genesis block because it does not have any certificate
  if (block0.getView() != 0) {
    std::vector<JBlock> blocksToExec;
    View view2 = block1.getJust().getCView();
    bool done = false;

    while (!done) {
      if (DEBUG1) std::cout << KBLU << nfo() << "checking whether " << view2 << " can be executed" << KNRM << std::endl;
      // retrive the block corresponding to block0's justification
      std::map<View,JBlock>::iterator it2 = this->jblocks.find(view2);
      if (it2 != this->jblocks.end()) { // if the block is not available, we'll have to handle this later
        JBlock block2 = (JBlock)it2->second;
        if (DEBUG1) std::cout << KBLU << nfo() << "found block at view " << view2 << KNRM << std::endl;

        // We can execute this block if it is not already executed
        if (!block2.isExecuted()) {
          Hash hash1 = block0.getJust().getCHash();
          Hash hash2 = block2.hash();
          // TO FIX
          if (true) { //hash1 == hash2) {
            blocksToExec.insert(blocksToExec.begin(),block2);
            // we see whether we can execute block2's certificate
            if (view2 == 0) { // the genesis block
              done = true;
            } else { block0 = block2; view2 = block2.getJust().getCView(); }
          } else {
            // hashes don't match so we stop because we cannot execute
            if (DEBUG0) std::cout << KBLU << nfo() << "hashes don't match at view " << view2 << ", clearing blocks to execute " << KNRM << std::endl;
            done = true;
            blocksToExec.clear();
          }
        } else {
          // If the block is already executed, we can stop and actually execute all the blocks we have collected so far
          done = true;
        }
      } else {
        // We don't have all the blocks, so we stop because we cannot execute
        if (DEBUG0) std::cout << KBLU << nfo() << "missing block at view " << view2 << ", clearing blocks to execute " << KNRM << std::endl;
        done = true;
        blocksToExec.clear();
      }
    }

    // We execute the blocks we recorded
    for (std::vector<JBlock>::iterator it = blocksToExec.begin(); it != blocksToExec.end(); ++it) {
      JBlock block2 = *it;
      View view2 = block2.getView();

      block2.markExecuted();  // We mark the block as being executed
      jblocks[view2]=block2;

      auto endView = std::chrono::steady_clock::now();
      double time = std::chrono::duration_cast<std::chrono::microseconds>(endView - startView).count();
      startView = endView;
      stats.incExecViews();
      stats.addTotalViewTime(time);
      this->viewsWithoutNewTrans++;
      stats.endExecTime(view2,endView);

      // Execute
      // TODO: We should wait until we received the block corresponding to the hash to execute
      if (DEBUG0 && DEBUGE) std::cout << KRED << nfo() << "CH-EXECUTE(" << view2 << ";" << this->viewsWithoutNewTrans << ";" << this->view << "/" << this->maxViews << ":" << time << ")" << stats.toString() << KNRM << std::endl;

      replyTransactions(block2.getTransactions()); // Reply
      if (DEBUG1) std::cout << KBLU << nfo() << "sent replies" << KNRM << std::endl;
    }

    if (timeToStop()) { recordStats(); }
  }
}

void Handler::voteCh(JBlock block) { // Votes for a block, sends the vote, and signs the prepared certif. and sends it
  if (DEBUG1) std::cout << KBLU << nfo() << "voting for " << block.prettyPrint() << KNRM << std::endl;

  this->jblocks[this->view]=block;
  stats.startExecTime(this->view,std::chrono::steady_clock::now());

  View view0 = block.getJust().getCView();
  if (DEBUG1) std::cout << KBLU << nfo() << "retriving block for view " << view0 << KNRM << std::endl;
  
  std::map<View,JBlock>::iterator it0 = this->jblocks.find(view0); // retrive the block corresponding to block's justification
  if (it0 != this->jblocks.end()) { // if the block is not available, we'll have to handle this later
    JBlock block0 = (JBlock)it0->second;
    if (DEBUG1) std::cout << KBLU << nfo() << "block for view " << view0 << " retrieved" << KNRM << std::endl;
    if (DEBUG1) std::cout << KBLU << nfo() << "block is: " << block0.prettyPrint() << KNRM << std::endl;

    View view1 = block0.getJust().getCView();
    if (DEBUG1) std::cout << KBLU << nfo() << "retriving block for view " << view1 << KNRM << std::endl;
    
    std::map<View,JBlock>::iterator it1 = this->jblocks.find(view1); // retrive the block corresponding to block0's justification
    if (it1 != this->jblocks.end()) { // if the block is not available, we'll have to handle this later
      JBlock block1 = (JBlock)it1->second;
      if (DEBUG1) std::cout << KBLU << nfo() << "block for view " << view1 << " retrieved" << KNRM << std::endl;

      Just justPrep = callTEEprepareCh(block,block0,block1);
      Just justNv2 = callTEEsignCh();

      if (DEBUG1) std::cout << KBLU << nfo() << "prepared & signed" << KNRM << std::endl;

      if (justPrep.getSigns().getSize() == 1) {
        Sign sigPrep = justPrep.getSigns().get(0);
        PID nextLeader = getLeaderOf(this->view+1);
        Peers recipientsNL = keep_from_peers(nextLeader);

        if (amLeaderOf(this->view)) { // leader of the current view, we send a MsgLdrPrepareCh
          MsgLdrPrepareCh msgPrep(block,sigPrep);
          Peers recipientsPrep = remove_from_peers(this->myid);
          sendMsgLdrPrepareCh(msgPrep,recipientsPrep);
        } else { // not the leader of the current view, we send a MsgPrepareCh
          MsgPrepareCh msgPrep(justPrep.getRData(),sigPrep);
          if (amLeaderOf(this->view+1)) { this->log.storePrepCh(msgPrep); } // If we're the leader of the next view, we store the message
          else { sendMsgPrepareCh(msgPrep,recipientsNL); } // Otherwise we send it
        }
        if (DEBUG1) std::cout << KBLU << nfo() << "sent vote" << KNRM << std::endl;

        if (justNv2.getSigns().getSize() == 1) {
          Sign sigNv = justNv2.getSigns().get(0);
          MsgNewViewCh msgNv(justNv2.getRData(),sigNv);
          if (amLeaderOf(this->view+1)) { this->log.storeNvCh(msgNv); } // If we're the leader of the next view, we store the message
          else { sendMsgNewViewCh(msgNv,recipientsNL); } // Otherwise we send it

          tryExecuteCh(block,block0,block1);

          // The leader of the next view stays in this view until it has received enough votes or timed out
          if (amLeaderOf(this->view+1)) { checkNewJustCh(justPrep.getRData()); }
          else {
            this->view++; // increment the view
            setTimer(); // reset the timer
            handleEarlierMessagesCh(); // try to handler already received messages
          }
        }
      } else {
        if (DEBUG1) std::cout << KLRED << nfo() << "prepare justification ill-formed:" << justPrep.prettyPrint() << KNRM << std::endl;
      }
    } else {
      if (DEBUG1) std::cout << KLRED << nfo() << "missing block for view " << view1 << KNRM << std::endl;
    }
  } else {
    if (DEBUG1) std::cout << KLRED << nfo() << "missing block for view " << view0 << KNRM << std::endl;
  }
}

void Handler::prepareCh() { // For leader to do begin a view (prepare phase) in Chained version
  if (DEBUG1) std::cout << KBLU << nfo() << "leader is preparing" << KNRM << std::endl;

  // If we don't have the latest certificate, we have to select one
  if (!this->justNV.isSet() || this->justNV.getRData().getPropv() != this->view-1) {
    // We first create a block that extends the highest prepared block
    this->justNV = this->log.findHighestNvCh(this->view-1);
  }

  JBlock block = createNewBlockCh();
  voteCh(block);
}

void Handler::checkNewJustCh(RData data) { // For leaders to check whether they can create a new (this->qsize)-justification
  Signs signs = (this->log).getPrepareCh(data.getPropv(),this->qsize);
  // We should not need to check the size of 'signs' as this function should only be called, when this is possible
  if (signs.getSize() == this->qsize) {
    this->justNV = Just(data,signs); // create the new justification
    this->view++; // increment the view
    setTimer(); // reset the timer
    prepareCh(); // start the new view
  }
}

void Handler::handleEarlierMessagesCh() { // handle stored MsgLdrPrepareCh messages
  if (amCurrentLeader()) {
  } else {
    MsgLdrPrepareCh msg = this->log.firstLdrPrepareCh(this->view);
    if (msg.sign.isSet()  // If we've stored the leader's proposal
        && this->jblocks.find(this->view) == this->jblocks.end()) { // we handle the message if we haven't done so already, i.e., we haven't stored the corresponding block
      if (DEBUG1) std::cout << KMAG << nfo() << "catching up using leader proposal (view=" << this->view << ")" << KNRM << std::endl;
      voteCh(msg.block);
    }
  }
}


void Handler::handleNewviewCh(MsgNewViewCh msg) {
  // NEW-VIEW messages are received by leaders
  // Once a leader has received 2f+1 new-view messages, it creates a proposal out of the highest prepared block
  // and sends this proposal in a PREPARE message
  auto start = std::chrono::steady_clock::now();
  if (DEBUG1) std::cout << KBLU << nfo() << "handling:" << msg.prettyPrint() << KNRM << std::endl;
  Hash   hashP = msg.data.getProph();
  View   viewP = msg.data.getPropv();
  Phase1 ph    = msg.data.getPhase();
  if (hashP.isDummy() && viewP+1 >= this->view && ph == PH1_NEWVIEW && amLeaderOf(viewP+1)) {
    if (viewP+1 == this->view // we're in the correct view
        && this->log.storeNvCh(msg) >= this->qsize // we've stored enough new-view messages to get started
        && this->jblocks.find(this->view) == this->jblocks.end()) { // we haven't prepared yet (i.e., we haven't generated a block for the current view yet)
      prepareCh();
    } else {
      // If the message is for later, we store it
      if (DEBUG1) std::cout << KMAG << nfo() << "storing(view=" << this->view << "):" << msg.prettyPrint() << KNRM << std::endl;
      this->log.storeNvCh(msg);
    }
  } else {
    if (DEBUG1) std::cout << KMAG << nfo() << "discarded(view=" << this->view << "):" << msg.prettyPrint() << KNRM << std::endl;
    if (DEBUG1) { std::cout << KMAG << nfo()
                            << "test1=" << hashP.isDummy() << ";"
                            << "test2=" << (viewP+1 >= this->view) << "(" << viewP+1 << "," << this->view << ");"
                            << "test3=" << (ph == PH1_NEWVIEW) << ";"
                            << "test4=" << amLeaderOf(viewP+1) << KNRM << std::endl; }
  }
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTotalHandleTime(time);
  stats.addTotalNvTime(time);
}

void Handler::handle_newview_ch(MsgNewViewCh msg, const PeerNet::conn_t &conn) {
  handleNewviewCh(msg);
}

void Handler::handleLdrPrepareCh(MsgLdrPrepareCh msg) { // Run by the backups in the prepare phase
  auto start = std::chrono::steady_clock::now();
  if (DEBUG1) std::cout << KBLU << nfo() << "handling(view=" << this->view << "):" << msg.prettyPrint() << KNRM << std::endl;

  JBlock block = msg.block;
  Sign sign    = msg.sign;
  View v       = block.getView();
  Just just    = ldrPrepareCh2just(msg);

  if (v >= this->view
      && !amLeaderOf(v) // v is the sender
      && Sverify(just.getSigns(),this->myid,this->nodes,just.getRData().toString())) {
    // We first store the ldrPrepare as well as the prepare message corresponding to the ldrPrepare message
    if (amLeaderOf(v+1)) {
      this->log.storePrepCh(MsgPrepareCh(just.getRData(),just.getSigns().get(0)));
    }
    if (v == this->view) {
      voteCh(block);
    } else {
      // If the message is for later, we store it
      if (DEBUG1) std::cout << KMAG << nfo() << "storing(view=" << this->view << "):" << msg.prettyPrint() << KNRM << std::endl;
      this->log.storeLdrPrepCh(msg);
      handleEarlierMessagesCh(); // We try to handle earlier messages in case we're still stuck earlier
    }
  } else {
    if (DEBUG1) std::cout << KMAG << nfo() << "discarded:" << msg.prettyPrint() << KNRM << std::endl;
  }

  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTotalHandleTime(time);
}

void Handler::handle_ldrprepare_ch(MsgLdrPrepareCh msg, const PeerNet::conn_t &conn) {
  if (DEBUGT) printNowTime("handling MsgLdrPrepareCh");
  handleLdrPrepareCh(msg);
}

void Handler::handlePrepareCh(MsgPrepareCh msg) { // For the leader of view this->view+1 to handle votes
  auto start = std::chrono::steady_clock::now();
  if (DEBUG1) std::cout << KBLU << nfo() << "handling:" << msg.prettyPrint() << KNRM << std::endl;

  RData data = msg.data;
  View v = data.getPropv();
  if (v == this->view) {
    if (amLeaderOf(v+1)) {
      // We store messages until we get enough of them to create a new justification
      // We wait to have received the block of the current view to generate a new justification
      //   otherwise we won't be able to preapre our block (we also need the previous block too)
      if (this->log.storePrepCh(msg) >= this->qsize
          && this->jblocks.find(this->view) != this->jblocks.end()) {
        checkNewJustCh(data);
      }
    }
  } else {
    if (DEBUG1) std::cout << KMAG << nfo() << "storing:" << msg.prettyPrint() << KNRM << std::endl;
    if (v > this->view) { log.storePrepCh(msg); }
  }

  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addTotalHandleTime(time);
}

void Handler::handle_prepare_ch(MsgPrepareCh msg, const PeerNet::conn_t &conn) {
  handlePrepareCh(msg);
}