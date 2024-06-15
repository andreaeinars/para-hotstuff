#ifndef TRUSTEDFUN_H
#define TRUSTEDFUN_H


#include "Hash.h"
#include "Just.h"
#include "Stats.h"


//AE-TODO add prefixlocked and extra vars if necessary
class TrustedFun {

 private:
  Hash   lockh;          // hash of the last locked block
  View   lockv;          // lockh's view
  Hash   preph;          // hash of the last prepared block
  View   prepv;          // preph's view
  Hash   latestPrepared; // hash of the latest prepared block
  View   latestPreparedView; // latestPrepared's view
  Hash   prefixLocked;   // hash of the prefix locked block
  View   prefixLockedView; // prefixLocked's view
  View   view;           // current view
  Phase1 phase;          // current phase
  PID    id;             // unique identifier
  KEY    priv;           // private key
  unsigned int qsize;    // quorum size

  Just sign(Hash h1, Hash h2, View v2);
  void increment();

 public:
  TrustedFun();
  TrustedFun(unsigned int id, KEY priv, unsigned int q);

  Just TEEsign(Stats &stats);
  Just TEEprepare(Stats &stats, Nodes nodes, Hash hash, Just just);
  Just TEEstore(Stats &stats, Nodes nodes, Just just);
  bool TEEverify(Stats &stats, Nodes nodes, Just just);
};


#endif
