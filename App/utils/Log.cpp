#include "Log.h"

Log::Log() {}

// checks that there are signatures from all the signers
template <typename T>
bool msgNewViewFrom(std::set<T> msgs, std::set<PID> signers) {
  for (typename std::set<T>::iterator it=msgs.begin(); it!=msgs.end(); ++it) {
    T msg = (T)*it;
    std::set<PID> k = msg.signs.getSigners();
    for (std::set<PID>::iterator it2=k.begin(); it2!=k.end(); ++it2) {
      signers.erase((PID)*it2);
      if (signers.empty()) { return true; }
    }
  }
  return false;
}

template <typename T>
bool msgPrepareFrom(std::set<T> msgs, std::set<PID> signers) {
  for (typename std::set<T>::iterator it=msgs.begin(); it!=msgs.end(); ++it) {
    T msg = (T)*it;
    std::set<PID> k = msg.signs.getSigners();
    for (std::set<PID>::iterator it2=k.begin(); it2!=k.end(); ++it2) {
      signers.erase((PID)*it2);
      if (signers.empty()) { return true; }
    }
  }
  return false;
}

template <typename T>
bool msgPreCommitFrom(std::set<T> msgs, std::set<PID> signers) {
  for (typename std::set<T>::iterator it=msgs.begin(); it!=msgs.end(); ++it) {
    T msg = (T)*it;
    std::set<PID> k = msg.signs.getSigners();
    for (std::set<PID>::iterator it2=k.begin(); it2!=k.end(); ++it2) {
      signers.erase((PID)*it2);
      if (signers.empty()) { return true; }
    }
  }
  return false;
}

template <typename T>
bool msgCommitFrom(std::set<T> msgs, std::set<PID> signers) {
  for (typename std::set<T>::iterator it=msgs.begin(); it!=msgs.end(); ++it) {
    T msg = (T)*it;
    std::set<PID> k = msg.signs.getSigners();
    for (std::set<PID>::iterator it2=k.begin(); it2!=k.end(); ++it2) {
      signers.erase((PID)*it2);
      if (signers.empty()) { return true; }
    }
  }
  return false;
}

// checks that there are signatures from all the signers
template <typename T>
bool msgLdrPrepareFrom(std::set<T> msgs, std::set<PID> signers) {
  for (typename std::set<T>::iterator it=msgs.begin(); it!=msgs.end(); ++it) {
    T msg = (T)*it;
    std::set<PID> k = msg.signs.getSigners();
    for (std::set<PID>::iterator it2=k.begin(); it2!=k.end(); ++it2) {
      signers.erase((PID)*it2);
      if (signers.empty()) { return true; }
    }
  }
  return false;
}

unsigned int Log::storeNv(MsgNewView msg) {
  RData rdata = msg.rdata;
  View v = rdata.getPropv();
  std::set<PID> signers = msg.signs.getSigners();

  std::map<View,std::set<MsgNewView>>::iterator it1 = this->newviews.find(v);
  if (it1 != this->newviews.end()) { // there is already an entry for this view
    std::set<MsgNewView> msgs = it1->second;

    // We only add 'msg' to the log if the sender hasn't already sent a new-view message for this view
    if (!msgNewViewFrom(msgs,signers)) {
      msgs.insert(msg);
      this->newviews[v]=msgs;
      //if (DEBUG) { std::cout << KGRN << "updated entry; #=" << msgs.size() << KNRM << std::endl; }
      return msgs.size();
      //k[hdr]=msgs;
      //log[v]=k;
    }
  } else { // there is no entry for this view
    this->newviews[v]={msg};
    if (DEBUG) { std::cout << KGRN << "no entry for this view (" << v << ") before; #=1" << KNRM << std::endl; }
    return 1;
  }

  return 0;
}

unsigned int Log::storePrep(MsgPrepare msg) {
  RData rdata = msg.rdata;
  View v = rdata.getPropv();
  std::set<PID> signers = msg.signs.getSigners();

  std::map<View,std::set<MsgPrepare>>::iterator it1 = this->prepares.find(v);
  if (it1 != this->prepares.end()) { // there is already an entry for this view
    std::set<MsgPrepare> msgs = it1->second;

    // We only add 'msg' to the log if the sender hasn't already sent a new-view message for this view
    if (!msgPrepareFrom(msgs,signers)) {
      msgs.insert(msg);
      this->prepares[v]=msgs;
      //if (DEBUG) { std::cout << KGRN << "updated entry; #=" << msgs.size() << KNRM << std::endl; }
      return msgs.size();
    }
  } else { // there is no entry for this view
    this->prepares[v]={msg};
    if (DEBUG) { std::cout << KGRN << "no entry for this view (" << v << ") before; #=1" << KNRM << std::endl; }
    return 1;
  }

  return 0;
}

unsigned int Log::storePc(MsgPreCommit msg) {
  RData rdata = msg.rdata;
  View v = rdata.getPropv();
  std::set<PID> signers = msg.signs.getSigners();

  std::map<View,std::set<MsgPreCommit>>::iterator it1 = this->precommits.find(v);
  if (it1 != this->precommits.end()) { // there is already an entry for this view
    std::set<MsgPreCommit> msgs = it1->second;

    // We only add 'msg' to the log if the sender hasn't already sent a pre-commits message for this view
    if (!msgPreCommitFrom(msgs,signers)) {
      msgs.insert(msg);
      this->precommits[v]=msgs;
      //if (DEBUG) { std::cout << KGRN << "updated entry; #=" << msgs.size() << KNRM << std::endl; }
      return msgs.size();
      //k[hdr]=msgs;
      //log[v]=k;
    }
  } else { // there is no entry for this view
    this->precommits[v]={msg};
    if (DEBUG) { std::cout << KGRN << "no entry for this view (" << v << ") before; #=1" << KNRM << std::endl; }
    return 1;
  }

  return 0;
}

unsigned int Log::storeCom(MsgCommit msg) {
  RData rdata = msg.rdata;
  View v = rdata.getPropv();
  std::set<PID> signers = msg.signs.getSigners();

  std::map<View,std::set<MsgCommit>>::iterator it1 = this->commits.find(v);
  if (it1 != this->commits.end()) { // there is already an entry for this view
    std::set<MsgCommit> msgs = it1->second;

    // We only add 'msg' to the log if the sender hasn't already sent a commits message for this view
    if (!msgCommitFrom(msgs,signers)) {
      msgs.insert(msg);
      this->commits[v]=msgs;
      //if (DEBUG) { std::cout << KGRN << "updated entry; #=" << msgs.size() << KNRM << std::endl; }
      return msgs.size();
      //k[hdr]=msgs;
      //log[v]=k;
    }
  } else { // there is no entry for this view
    this->commits[v]={msg};
    if (DEBUG) { std::cout << KGRN << "no entry for this view (" << v << ") before; #=1" << KNRM << std::endl; }
    return 1;
  }

  return 0;
}

unsigned int Log::storeProp(MsgLdrPrepare msg) {
  Proposal prop = msg.prop;
  View v = prop.getJust().getRData().getPropv();
  std::set<PID> signers = msg.signs.getSigners();

  std::map<View,std::set<MsgLdrPrepare>>::iterator it1 = this->proposals.find(v);
  if (it1 != this->proposals.end()) { // there is already an entry for this view
    std::set<MsgLdrPrepare> msgs = it1->second;

    // We only add 'msg' to the log if the sender hasn't already sent a proposal message for this view
    if (!msgLdrPrepareFrom(msgs,signers)) {
      msgs.insert(msg);
      this->proposals[v]=msgs;
      //if (DEBUG) { std::cout << KGRN << "updated entry; #=" << msgs.size() << KNRM << std::endl; }
      return msgs.size();
      //k[hdr]=msgs;
      //log[v]=k;
    }
  } else { // there is no entry for this view
    this->proposals[v]={msg};
    if (DEBUG) { std::cout << KGRN << "no entry for this view (" << v << ") before; #=1" << KNRM << std::endl; }
    return 1;
  }

  return 0;
}

std::string Log::prettyPrint() {
  std::string text;
  // newviews
  for (std::map<View,std::set<MsgNewView>>::iterator it1=this->newviews.begin(); it1!=this->newviews.end();++it1) {
    View v = it1->first;
    std::set<MsgNewView> msgs = it1->second;
    text += "newviews;view=" + std::to_string(v) + ";#=" + std::to_string(msgs.size()) + "\n";
  }
  //prepares
  for (std::map<View,std::set<MsgPrepare>>::iterator it1=this->prepares.begin(); it1!=this->prepares.end();++it1) {
    View v = it1->first;
    std::set<MsgPrepare> msgs = it1->second;
    text += "prepares;view=" + std::to_string(v) + ";#=" + std::to_string(msgs.size()) + "\n";
  }
  //precommits
  for (std::map<View,std::set<MsgPreCommit>>::iterator it1=this->precommits.begin(); it1!=this->precommits.end();++it1) {
    View v = it1->first;
    std::set<MsgPreCommit> msgs = it1->second;
    text += "precommits;view=" + std::to_string(v) + ";#=" + std::to_string(msgs.size()) + "\n";
  }
  //commits
  for (std::map<View,std::set<MsgCommit>>::iterator it1=this->commits.begin(); it1!=this->commits.end();++it1) {
    View v = it1->first;
    std::set<MsgCommit> msgs = it1->second;
    text += "commits;view=" + std::to_string(v) + ";#=" + std::to_string(msgs.size()) + "\n";
  }
  //proposals
  for (std::map<View,std::set<MsgLdrPrepare>>::iterator it1=this->proposals.begin(); it1!=this->proposals.end();++it1) {
    View v = it1->first;
    std::set<MsgLdrPrepare> msgs = it1->second;
    text += "proposals;view=" + std::to_string(v) + ";#=" + std::to_string(msgs.size()) + "\n";
  }

  return text;
}

Just Log::findHighestNv(View view) {
  std::map<View,std::set<MsgNewView>>::iterator it1 = this->newviews.find(view);
  Just just = Just();
  if (it1 != this->newviews.end()) { // there is already an entry for this view
    std::set<MsgNewView> msgs = it1->second;
    View h = 0;
    for (std::set<MsgNewView>::iterator it=msgs.begin(); it!=msgs.end(); ++it) {
      MsgNewView msg = (MsgNewView)*it;
      RData rdata = msg.rdata;
      Signs signs = msg.signs;
      View v = rdata.getJustv();
      if (v >= h) { h = v; just = Just(rdata,signs); }
    }
  }
  return just;
}

Just Log::firstPrepare(View view) {
  std::map<View,std::set<MsgPrepare>>::iterator it1 = this->prepares.find(view);
  Just just = Just();
  if (it1 != this->prepares.end()) { // there is already an entry for this view
    std::set<MsgPrepare> msgs = it1->second;
    if (0 < msgs.size()) { // We return the first element
      std::set<MsgPrepare>::iterator it=msgs.begin();
      MsgPrepare msg = (MsgPrepare)*it;
      RData rdata = msg.rdata;
      Signs signs = msg.signs;
      return Just(rdata,signs);
    }
  }
  return just;
}

Just Log::firstPrecommit(View view) {
  std::map<View,std::set<MsgPreCommit>>::iterator it1 = this->precommits.find(view);
  Just just = Just();
  if (it1 != this->precommits.end()) { // there is already an entry for this view
    std::set<MsgPreCommit> msgs = it1->second;
    if (0 < msgs.size()) { // We return the first element
      std::set<MsgPreCommit>::iterator it=msgs.begin();
      MsgPreCommit msg = (MsgPreCommit)*it;
      RData rdata = msg.rdata;
      Signs signs = msg.signs;
      return Just(rdata,signs);
    }
  }
  return just;
}

Just Log::firstCommit(View view) {
  std::map<View,std::set<MsgCommit>>::iterator it1 = this->commits.find(view);
  Just just = Just();
  if (it1 != this->commits.end()) { // there is already an entry for this view
    std::set<MsgCommit> msgs = it1->second;
    if (0 < msgs.size()) { // We return the first element
      std::set<MsgCommit>::iterator it=msgs.begin();
      MsgCommit msg = (MsgCommit)*it;
      RData rdata = msg.rdata;
      Signs signs = msg.signs;
      return Just(rdata,signs);
    }
  }
  return just;
}

MsgLdrPrepare Log::firstProposal(View view) {
  std::map<View,std::set<MsgLdrPrepare>>::iterator it1 = this->proposals.find(view);
  MsgLdrPrepare msg;
  if (it1 != this->proposals.end()) { // there is already an entry for this view
    std::set<MsgLdrPrepare> msgs = it1->second;
    if (0 < msgs.size()) { // We return the first element
      std::set<MsgLdrPrepare>::iterator it=msgs.begin();
      MsgLdrPrepare msg = (MsgLdrPrepare)*it;
      return msg;
    }
  }
  return msg;
}

Signs Log::getNewView(View view, unsigned int n) {
  Signs signs;
  std::map<View,std::set<MsgNewView>>::iterator it1 = this->newviews.find(view);
  if (it1 != this->newviews.end()) { // there is already an entry for this view
    std::set<MsgNewView> msgs = it1->second;
    for (std::set<MsgNewView>::iterator it=msgs.begin(); signs.getSize() < n && it!=msgs.end(); ++it) {
      MsgNewView msg = (MsgNewView)*it;
      Signs others = msg.signs;
      //if (DEBUG) std::cout << KMAG << "adding-log-prep-signatures: " << others.prettyPrint() << KNRM << std::endl;
      signs.addUpto(others,n);
    }
  }
  //if (DEBUG) std::cout << KMAG << "log-prep-signatures: " << signs.prettyPrint() << KNRM << std::endl;
  return signs;
}

Signs Log::getPrepare(View view, unsigned int n) {
  Signs signs;
  std::map<View,std::set<MsgPrepare>>::iterator it1 = this->prepares.find(view);
  if (it1 != this->prepares.end()) { // there is already an entry for this view
    std::set<MsgPrepare> msgs = it1->second;
    for (std::set<MsgPrepare>::iterator it=msgs.begin(); signs.getSize() < n && it!=msgs.end(); ++it) {
      MsgPrepare msg = (MsgPrepare)*it;
      Signs others = msg.signs;
      //if (DEBUG) std::cout << KMAG << "adding-log-prep-signatures: " << others.prettyPrint() << KNRM << std::endl;
      signs.addUpto(others,n);
    }
  }
  //if (DEBUG) std::cout << KMAG << "log-prep-signatures: " << signs.prettyPrint() << KNRM << std::endl;
  return signs;
}

Signs Log::getPrecommit(View view, unsigned int n) {
  Signs signs;
  std::map<View,std::set<MsgPreCommit>>::iterator it1 = this->precommits.find(view);
  if (it1 != this->precommits.end()) { // there is already an entry for this view
    std::set<MsgPreCommit> msgs = it1->second;
    for (std::set<MsgPreCommit>::iterator it=msgs.begin(); signs.getSize() < n && it!=msgs.end(); ++it) {
      MsgPreCommit msg = (MsgPreCommit)*it;
      Signs others = msg.signs;
      //if (DEBUG) std::cout << KMAG << "adding-log-pc-signatures: " << others.prettyPrint() << KNRM << std::endl;
      signs.addUpto(others,n);
    }
  }
  return signs;
}

Signs Log::getCommit(View view, unsigned int n) {
  Signs signs;
  std::map<View,std::set<MsgCommit>>::iterator it1 = this->commits.find(view);
  if (it1 != this->commits.end()) { // there is already an entry for this view
    std::set<MsgCommit> msgs = it1->second;
    for (std::set<MsgCommit>::iterator it=msgs.begin(); signs.getSize() < n && it!=msgs.end(); ++it) {
      MsgCommit msg = (MsgCommit)*it;
      Signs others = msg.signs;
      //if (DEBUG) std::cout << KMAG << "adding-log-com-signatures: " << others.prettyPrint() << KNRM << std::endl;
      signs.addUpto(others,n);
    }
  }
  return signs;
}

//CHAINED

bool msgNewViewChFrom(std::set<MsgNewViewCh> msgs, PID signer) {
  for (std::set<MsgNewViewCh>::iterator it=msgs.begin(); it!=msgs.end(); ++it) {
    MsgNewViewCh msg = (MsgNewViewCh)*it;
    PID k = msg.sign.getSigner();
    if (signer == k) { return true; }
  }
  return false;
}

bool msgPrepareChFrom(std::set<MsgPrepareCh> msgs, PID signer) {
  for (std::set<MsgPrepareCh>::iterator it=msgs.begin(); it!=msgs.end(); ++it) {
    MsgPrepareCh msg = (MsgPrepareCh)*it;
    PID k = msg.sign.getSigner();
    if (signer == k) { return true; }
  }
  return false;
}

bool msgLdrPrepareChFrom(std::set<MsgLdrPrepareCh> msgs, PID signer) {
  for (std::set<MsgLdrPrepareCh>::iterator it=msgs.begin(); it!=msgs.end(); ++it) {
    MsgLdrPrepareCh msg = (MsgLdrPrepareCh)*it;
    PID k = msg.sign.getSigner();
    if (signer == k) { return true; }
  }
  return false;
}

unsigned int Log::storeNvCh(MsgNewViewCh msg) {
  RData data = msg.data;
  View v = data.getPropv();
  PID signer = msg.sign.getSigner();

  std::map<View,std::set<MsgNewViewCh>>::iterator it1 = this->newviewsCh.find(v);
  if (it1 != this->newviewsCh.end()) { // there is already an entry for this view
    std::set<MsgNewViewCh> msgs = it1->second;

    // We only add 'msg' to the log if the sender hasn't already sent a new-view message for this view
    if (!msgNewViewChFrom(msgs,signer)) {
      msgs.insert(msg);
      this->newviewsCh[v]=msgs;
      if (DEBUG) { std::cout << KGRN << "updated entry; #=" << msgs.size() << KNRM << std::endl; }
      return msgs.size();
    }
  } else { // there is no entry for this view
    this->newviewsCh[v]={msg};
    if (DEBUG) { std::cout << KGRN << "no entry for this view (" << v << ") before; #=1" << KNRM << std::endl; }
    return 1;
  }

  return 0;
}

std::set<MsgNewViewCh> Log::getNewViewCh(View view, unsigned int n) {
  std::set<MsgNewViewCh> ret;
  std::map<View,std::set<MsgNewViewCh>>::iterator it1 = this->newviewsCh.find(view);
  if (it1 != this->newviewsCh.end()) { // there is already an entry for this view
    std::set<MsgNewViewCh> msgs = it1->second;
    for (std::set<MsgNewViewCh>::iterator it=msgs.begin(); ret.size() < n && it!=msgs.end(); ++it) {
      MsgNewViewCh msg = (MsgNewViewCh)*it;
      ret.insert(msg);
    }
  }
  return ret;
}

unsigned int Log::storePrepCh(MsgPrepareCh msg) {
  RData data = msg.data;
  View v = data.getPropv();
  PID signer = msg.sign.getSigner();

  std::map<View,std::set<MsgPrepareCh>>::iterator it1 = this->preparesCh.find(v);
  if (it1 != this->preparesCh.end()) { // there is already an entry for this view
    std::set<MsgPrepareCh> msgs = it1->second;

    // We only add 'msg' to the log if the sender hasn't already sent a new-view message for this view
    if (!msgPrepareChFrom(msgs,signer)) {
      msgs.insert(msg);
      this->preparesCh[v]=msgs;
      //if (DEBUG) { std::cout << KGRN << "updated entry; #=" << msgs.size() << KNRM << std::endl; }
      return msgs.size();
    }
  } else { // there is no entry for this view
    this->preparesCh[v]={msg};
    if (DEBUG) { std::cout << KGRN << "no entry for this view (" << v << ") before; #=1" << KNRM << std::endl; }
    return 1;
  }

  return 0;
}

unsigned int Log::storeLdrPrepCh(MsgLdrPrepareCh msg) {
  JBlock block = msg.block;
  View v = block.getView();
  PID signer = msg.sign.getSigner();

  std::map<View,std::set<MsgLdrPrepareCh>>::iterator it1 = this->ldrpreparesCh.find(v);
  if (it1 != this->ldrpreparesCh.end()) { // there is already an entry for this view
    std::set<MsgLdrPrepareCh> msgs = it1->second;

    // We only add 'msg' to the log if the sender hasn't already sent a new-view message for this view
    if (!msgLdrPrepareChFrom(msgs,signer)) {
      msgs.insert(msg);
      this->ldrpreparesCh[v]=msgs;
      //if (DEBUG) { std::cout << KGRN << "updated entry; #=" << msgs.size() << KNRM << std::endl; }
      return msgs.size();
    }
  } else { // there is no entry for this view
    this->ldrpreparesCh[v]={msg};
    if (DEBUG) { std::cout << KGRN << "no entry for this view (" << v << ") before; #=1" << KNRM << std::endl; }
    return 1;
  }

  return 0;
}

Signs Log::getPrepareCh(View view, unsigned int n) {
  Signs signs;
  std::map<View,std::set<MsgPrepareCh>>::iterator it1 = this->preparesCh.find(view);
  if (it1 != this->preparesCh.end()) { // there is already an entry for this view
    std::set<MsgPrepareCh> msgs = it1->second;
    for (std::set<MsgPrepareCh>::iterator it=msgs.begin(); signs.getSize() < n && it!=msgs.end(); ++it) {
      MsgPrepareCh msg = (MsgPrepareCh)*it;
      Signs others = Signs(msg.sign);
      signs.addUpto(others,n);
    }
  }
  return signs;
}

Just Log::findHighestNvCh(View view) {
  std::map<View,std::set<MsgNewViewCh>>::iterator it1 = this->newviewsCh.find(view);
  Just just = Just();
  if (it1 != this->newviewsCh.end()) { // there is already an entry for this view
    std::set<MsgNewViewCh> msgs = it1->second;
    View h = 0;
    for (std::set<MsgNewViewCh>::iterator it=msgs.begin(); it!=msgs.end(); ++it) {
      MsgNewViewCh msg = (MsgNewViewCh)*it;
      RData data = msg.data;
      Sign sign = msg.sign;
      View v = data.getJustv();
      if (v >= h) { h = v; just = Just(data,{sign}); }
    }
  }
  return just;
}

MsgLdrPrepareCh Log::firstLdrPrepareCh(View view) {
  std::map<View,std::set<MsgLdrPrepareCh>>::iterator it = this->ldrpreparesCh.find(view);
  if (it != this->ldrpreparesCh.end()) { // there is already an entry for this view
    std::set<MsgLdrPrepareCh> msgs = it->second;
    if (0 < msgs.size()) { // We return the first element
      return (MsgLdrPrepareCh)*(msgs.begin());
    }
  }
  return MsgLdrPrepareCh(JBlock(),Sign());
}

// PARALLEL

// AE-TODO Untested
unsigned int Log::storeNvPara(MsgNewViewPara msg) {
  RDataPara rdata = msg.rdata;
  View v = rdata.getPropv();
  std::set<PID> signers = msg.signs.getSigners();

  std::map<View,std::set<MsgNewViewPara>>::iterator it1 = this->newviewsPara.find(v);
  if (it1 != this->newviewsPara.end()) { // there is already an entry for this view
    std::set<MsgNewViewPara> msgs = it1->second;

    // We only add 'msg' to the log if the sender hasn't already sent a new-view message for this view
    if (!msgNewViewFrom(msgs,signers)) {
      msgs.insert(msg);
      this->newviewsPara[v]=msgs;
      //if (DEBUG) { std::cout << KGRN << "updated entry; #=" << msgs.size() << KNRM << std::endl; }
      return msgs.size();
    }
  } else { // there is no entry for this view
    this->newviewsPara[v]={msg};
    if (DEBUG) { std::cout << KGRN << "no entry for this view (" << v << ") before; #=1" << KNRM << std::endl; }
    return 1;
  }

  return 0;
}

//AE-TODO Untested
unsigned int Log::storePrepPara(MsgPreparePara msg) {
    RDataPara rdata = msg.rdata;
    View v = rdata.getPropv();
    unsigned int seqNumber = rdata.getSeqNumber();
    std::set<PID> signers = msg.signs.getSigners();

    auto it1 = this->preparesPara.find(v);
    if (it1 == this->preparesPara.end()) {
        this->preparesPara[v] = std::map<unsigned int, std::set<MsgPreparePara>>();
        it1 = this->preparesPara.find(v);
    }

    auto &viewMap = it1->second;
    auto it2 = viewMap.find(seqNumber);
    if (it2 == viewMap.end()) {
        viewMap[seqNumber] = std::set<MsgPreparePara>();
        it2 = viewMap.find(seqNumber);
    }

    auto &msgs = it2->second;
    if (!msgPrepareFrom(msgs, signers)) {
        msgs.insert(msg);
    }
    return msgs.size();
}


//AE-TODO Untested
unsigned int Log::storePcPara(MsgPreCommitPara msg) {
    RDataPara rdata = msg.rdata;
    View v = rdata.getPropv();
    unsigned int seqNumber = rdata.getSeqNumber();
    std::set<PID> signers = msg.signs.getSigners();

    auto it1 = this->precommitsPara.find(v);
    if (it1 == this->precommitsPara.end()) {
        this->precommitsPara[v] = std::map<unsigned int, std::set<MsgPreCommitPara>>();
        it1 = this->precommitsPara.find(v);
    }

    auto &viewMap = it1->second;
    auto it2 = viewMap.find(seqNumber);
    if (it2 == viewMap.end()) {
        viewMap[seqNumber] = std::set<MsgPreCommitPara>();
        it2 = viewMap.find(seqNumber);
    }

    auto &msgs = it2->second;
    if (!msgPreCommitFrom(msgs, signers)) {
        msgs.insert(msg);
    }
    return msgs.size();
}


//AE-TODO Untested
unsigned int Log::storeComPara(MsgCommitPara msg) {
    RDataPara rdata = msg.rdata;
    View v = rdata.getPropv();
    unsigned int seqNumber = rdata.getSeqNumber();
    std::set<PID> signers = msg.signs.getSigners();

    auto it1 = this->commitsPara.find(v);
    if (it1 == this->commitsPara.end()) {
        this->commitsPara[v] = std::map<unsigned int, std::set<MsgCommitPara>>();
        it1 = this->commitsPara.find(v);
    }

    auto &viewMap = it1->second;
    auto it2 = viewMap.find(seqNumber);
    if (it2 == viewMap.end()) {
        viewMap[seqNumber] = std::set<MsgCommitPara>();
        it2 = viewMap.find(seqNumber);
    }

    auto &msgs = it2->second;
    if (!msgCommitFrom(msgs, signers)) {
        msgs.insert(msg);
    }
    return msgs.size();
}


//AE-TODO Untested
unsigned int Log::storePropPara(MsgLdrPreparePara msg) {
    ParaProposal prop = msg.prop;
    View v = prop.getJust().getRDataPara().getPropv();
    unsigned int seqNumber = prop.getJust().getRDataPara().getSeqNumber();
    std::set<PID> signers = msg.signs.getSigners();

    auto it1 = this->proposalsPara.find(v);
    if (it1 == this->proposalsPara.end()) {
        this->proposalsPara[v] = std::map<unsigned int, std::set<MsgLdrPreparePara>>();
        it1 = this->proposalsPara.find(v);
    }

    auto &viewMap = it1->second;
    auto it2 = viewMap.find(seqNumber);
    if (it2 == viewMap.end()) {
        viewMap[seqNumber] = std::set<MsgLdrPreparePara>();
        it2 = viewMap.find(seqNumber);
    }

    auto &msgs = it2->second;
    if (!msgLdrPrepareFrom(msgs, signers)) {
        msgs.insert(msg);
    }
    return msgs.size();
}


//AE-TODO : Make sure this is correct
Just Log::findHighestNvPara(View view) {
    std::map<View,std::set<MsgNewViewPara>>::iterator it1 = this->newviewsPara.find(view);
    Just just = Just();
    if (it1 != this->newviewsPara.end()) { // there is already an entry for this view
        std::set<MsgNewViewPara> &msgs = it1->second;
        View highestView = 0;
        std::optional<unsigned int> highestSeqNumber = std::nullopt;
        for (const auto& msg : msgs) {
            RDataPara rdata = msg.rdata;
            Signs signs = msg.signs;
            View currentView = rdata.getJustv();
            unsigned int currentSeqNumber = rdata.getSeqNumber();

            // Check if the current message has a higher view or, if views are equal, a higher sequence number
            if (currentView > highestView || 
                (currentView == highestView && (!highestSeqNumber || (currentSeqNumber  > *highestSeqNumber)))) {
                highestView = currentView;
                highestSeqNumber = currentSeqNumber;
                just = Just(rdata, signs);
            }
        }
    }
    return just;
}


//AE-TODO: Find new views with matchnig view and sequence number
Signs Log::getNewViewPara(View view, unsigned int n, unsigned int seqNumber) {
  Signs signs;
  std::map<View,std::set<MsgNewViewPara>>::iterator it1 = this->newviewsPara.find(view);
  if (it1 != this->newviewsPara.end()) { // there is already an entry for this view
    std::set<MsgNewViewPara> msgs = it1->second;
    for (std::set<MsgNewViewPara>::iterator it=msgs.begin(); signs.getSize() < n && it!=msgs.end(); ++it) {
      MsgNewViewPara msg = (MsgNewViewPara)*it;
      Signs others = msg.signs;
      signs.addUpto(others,n);
    }
  }
  return signs;
}

// AE-TODO: Find first prepare with matching view and sequence number
Signs Log::getPreparePara(View view, unsigned int n, unsigned int seqNumber) {
    Signs signs;
    auto it1 = this->preparesPara.find(view);
    if (it1 != this->preparesPara.end()) { // there is already an entry for this view
        auto &viewMap = it1->second;
        auto it2 = viewMap.find(seqNumber);
        if (it2 != viewMap.end()) { // there is already an entry for this sequence number
            std::set<MsgPreparePara> &msgs = it2->second;
            for (auto it = msgs.begin(); signs.getSize() < n && it != msgs.end(); ++it) {
                MsgPreparePara msg = *it;
                Signs others = msg.signs;
                signs.addUpto(others, n);
            }
        }
    }
    return signs;
}

// AE-TODO: Find first precommit with matching view and sequence number
Signs Log::getPrecommitPara(View view, unsigned int n, unsigned int seqNumber) {
  Signs signs;
    auto it1 = this->precommitsPara.find(view);
    if (it1 != this->precommitsPara.end()) { // there is already an entry for this view
        auto &viewMap = it1->second;
        auto it2 = viewMap.find(seqNumber);
        if (it2 != viewMap.end()) { // there is already an entry for this sequence number
            std::set<MsgPreCommitPara> &msgs = it2->second;
            for (auto it = msgs.begin(); signs.getSize() < n && it != msgs.end(); ++it) {
                MsgPreCommitPara msg = *it;
                Signs others = msg.signs;
                signs.addUpto(others, n);
            }
        }
    }
    return signs;
}

// AE-TODO: Find first commit with matching view and sequence number
Signs Log::getCommitPara(View view, unsigned int n, unsigned int seqNumber) {
    Signs signs;
    auto it1 = this->commitsPara.find(view);
    if (it1 != this->commitsPara.end()) { // there is already an entry for this view
        auto &viewMap = it1->second;
        auto it2 = viewMap.find(seqNumber);
        if (it2 != viewMap.end()) { // there is already an entry for this sequence number
            std::set<MsgCommitPara> &msgs = it2->second;
            for (auto it = msgs.begin(); signs.getSize() < n && it != msgs.end(); ++it) {
                MsgCommitPara msg = *it;
                Signs others = msg.signs;
                signs.addUpto(others, n);
            }
        }
    }
    return signs;
}

bool Log::hasPrecommitForSeq(View view, unsigned int seqNumber) {
  auto it = this->precommitsPara.find(view);
  if (it != this->precommitsPara.end()) {
    const std::map<unsigned int, std::set<MsgPreCommitPara>>& seqMap = it->second;
    auto seqIt = seqMap.find(seqNumber);
    return seqIt != seqMap.end() && !seqIt->second.empty();
  }
  return false;
}