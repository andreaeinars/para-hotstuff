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
  unsigned int latestPreparedSeqNumber;
  Hash   prefixLockedHash;   // hash of the prefix locked block
  View   prefixLockedView; // prefixLocked's view
  unsigned int prefixLockedSeqNumber;
  View   view;           // current view
  Phase1 phase;          // current phase
  std::map<Hash, Phase1> blockPhases; 
  PID    id;             // unique identifier
  KEY    priv;           // private key
  unsigned int qsize;    // quorum size
  std::map<unsigned int, Hash> precommitBlocks; // Map to store precommit blocks by their sequence number
  std::set<unsigned int> precommitSeqNumbers; 
  std::map<unsigned int, View> precommitViews;

  Just sign(Hash h1, Hash h2, View v2, unsigned int seqNumber);
  Just signBlock(Hash h1, Hash h2, View v2, unsigned int seqNumber);
  void increment_block_phase(Hash blockHash);

 public:
  void increment_node_phase();
  void increment_view();
  void set_phase(Phase1 phase);
  TrustedPara();
  TrustedPara(unsigned int id, KEY priv, unsigned int q);

  Just TEEsign(Stats &stats);
  Just TEEsignBlock(Stats &stats, Hash blockHash);
  
  Just TEEprepare(Stats &stats, Nodes nodes, PBlock block, Just just);
  Just TEEstore(Stats &stats, Nodes nodes, Just just);
  bool TEEverify(Stats &stats, Nodes nodes, Just just);
  Just TEEverifyLeaderQC(Stats &stats, Nodes nodes, Just just, const std::vector<Hash> &blockHashes);
};


#endif
