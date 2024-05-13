#ifndef TRUSTEDPARA_H
#define TRUSTEDPARA_H

#include "Hash.h"
#include "Just.h"
#include "Stats.h"
#include "PBlock.h"

// AE-TODO
class TrustedPara {

 private:
  Hash   latestPreparedHash; // hash of the latest prepared block
  View   latestPreparedView; // latestPrepared's view
  Hash   prefixLockedHash;   // hash of the prefix locked block
  View   prefixLockedView; // prefixLocked's view
  View   view;           // current view
  Phase1 phase;          // current phase
  std::map<Hash, Phase1> blockPhases; 
  PID    id;             // unique identifier
  KEY    priv;           // private key
  unsigned int qsize;    // quorum size

  Just sign(Hash h1, Hash h2, View v2);
  Just signBlock(Hash h1, Hash h2, View v2, unsigned int seqNumber);
  void increment_node_phase();
  void increment_block_phase(Hash blockHash);

 public:
  TrustedPara();
  TrustedPara(unsigned int id, KEY priv, unsigned int q);

  Just TEEsign(Stats &stats);
  Just TEEsignBlock(Stats &stats, Hash blockHash);
  
  Just TEEprepare(Stats &stats, Nodes nodes, PBlock block, Just just);
  Just TEEstore(Stats &stats, Nodes nodes, Just just, bool allBlocksRecieved);
  bool TEEverify(Stats &stats, Nodes nodes, Just just);
  Just TEEverifyLeaderQC(Stats &stats, Nodes nodes, Just just, const std::vector<Hash> &blockHashes);
};


#endif
