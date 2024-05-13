#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <string>
#include <cstring>

#include "TrustedPara.h"


TrustedPara::TrustedPara() {
  this->latestPreparedHash = Hash(true); // the genesis block
  this->latestPreparedView = 0;
  this->prefixLockedHash = Hash(true); // the genesis block
  this->prefixLockedView = 0;
  this->view   = 0;
  this->phase  = PH1_NEWVIEW;
  this->qsize  = 0;
}

TrustedPara::TrustedPara(PID id, KEY priv, unsigned int q) {
  this->latestPreparedHash = Hash(true); // the genesis block
  this->latestPreparedView = 0;
  this->prefixLockedHash = Hash(true); // the genesis block
  this->prefixLockedView = 0;
  this->view   = 0;
  this->phase  = PH1_NEWVIEW;
  this->id     = id;
  this->priv   = priv;
  this->qsize  = q;
}


// increments the (view,phase) pair
void TrustedPara::increment_node_phase() {
  if (this->phase == PH1_NEWVIEW) {
    this->phase = PH1_PARALLEL; //AE-TODO: Make sure the phases make sense
  } else if (this->phase == PH1_RECOVER) {
    this->phase = PH1_VERIFY;
  } else if (this->phase == PH1_VERIFY) {
    this->phase = PH1_PARALLEL;
  } else if (this->phase == PH1_PARALLEL) {
    this->phase = PH1_NEWVIEW;
    this->view++;
  }
}

void TrustedPara::increment_block_phase(Hash blockHash) {
  if (blockPhases.find(blockHash) == blockPhases.end()) { //AE-TODO: Not sure this is needed
        blockPhases[blockHash] = PH1_PREPARE;
  }
  Phase1 &blockPhase = blockPhases[blockHash];
  if (blockPhase == PH1_PREPARE) {
      blockPhase = PH1_PRECOMMIT;
  } else if (blockPhase == PH1_PRECOMMIT) {
      blockPhase = PH1_COMMIT;
  } else if (blockPhase == PH1_COMMIT) {
      blockPhase = PH1_PREPARE;
  }
}

Just TrustedPara::sign(Hash h1, Hash h2, View v2) {
  RDataPara rdata(h1,this->view,h2,v2,this->phase, 0); //todo add sequnce number
  Sign sign(this->priv,this->id,rdata.toString());
  Just just(rdata,sign);
  increment_block_phase(h1);
  if (DEBUG) std::cout << "Signing: " << just.getRDataPara().prettyPrint() << std::endl;
  return just;
}

Just TrustedPara::signBlock(Hash h1, Hash h2, View v2, unsigned int seqNumber) {
   if (blockPhases.find(h1) == blockPhases.end()) { //AE-TODO: Not sure this is needed
        blockPhases[h1] = PH1_PREPARE;
  }
  Phase1 ph = blockPhases[h1];
  if (DEBUG) std::cout << "Signing with phase: " << ph << std::endl;
  RDataPara rdata(h1,this->view,h2,v2,ph, seqNumber); //todo add sequnce number
  Sign sign(this->priv,this->id,rdata.toString());
  Just just(rdata,sign);
  increment_block_phase(h1);
  if (DEBUG) std::cout << "Signing: " << just.getRDataPara().prettyPrint() << std::endl;
  return just;
}

Just TrustedPara::TEEsign(Stats &stats) {
  auto start = std::chrono::steady_clock::now();
  Just j = sign(Hash(false),this->latestPreparedHash,this->latestPreparedView); // AE-TODO: Actuaclly implement this
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addCryptoSignTime(time);
  return j;
}

bool TrustedPara::TEEverify(Stats &stats, Nodes nodes, Just just) {
  auto start = std::chrono::steady_clock::now();
  bool b = just.getSigns().verify(stats,this->id,nodes,just.getRDataPara().toString());
  auto end = std::chrono::steady_clock::now();
  double time = std::chrono::duration_cast<std::chrono::microseconds>(end - start).count();
  stats.addCryptoVerifTime(time);
  return b;
}

Just TrustedPara::TEEverifyLeaderQC(Stats &stats, Nodes nodes, Just just, const std::vector<Hash> &blockHashes) {
  RDataPara  rd = just.getRDataPara();
  Hash   h2 = rd.getJusth();
  View   v2 = rd.getJustv();
  Phase1 ph = rd.getPhase();

  bool prefixLockedInHashes;
  if (v2 == 0) {
    prefixLockedInHashes = true;
  } else {
    prefixLockedInHashes = std::find(blockHashes.begin(), blockHashes.end(), this->prefixLockedHash) != blockHashes.end();
  }

  bool teeverif_result = TEEverify(stats, nodes, just);
  bool eq_views_result = this->view == rd.getPropv();
  bool eq_phases_result = ph == PH1_NEWVIEW;
  bool safety_result = prefixLockedInHashes || v2 > this->prefixLockedView;

  if (DEBUG) {
    std::cout << "TEEverify result: " << teeverif_result << std::endl;
    std::cout << "eq_views result: " << eq_views_result << " (this->view: " << this->view << ", rd.getPropv(): " << rd.getPropv() << ")" << std::endl;
    std::cout << "eq_phases result: " << eq_phases_result << " (ph: " << ph << ", PH1_NEWVIEW: " << PH1_NEWVIEW << ")" << std::endl;
    std::cout << "safety result: " << safety_result << " (prefixLockedInHashes: " << prefixLockedInHashes << ", v2: " << v2 << ", this->prefixLockedView: " << this->prefixLockedView << ")" << std::endl;
  }

   if (teeverif_result
      && eq_views_result
      && eq_phases_result
      && safety_result) {
    // return sign(hash, h2, v2);
    // increment_node_phase(); //Go to VERIFY phase
    return just;
  } 
  else {
    if (DEBUG) std::cout << KMAG << "TEEverifyProposal failed:"
                         << "TEEverif="   << std::to_string(TEEverify(stats, nodes, just))
                         << ";eq-views="  << std::to_string(this->view == rd.getPropv())
                         << ";eq-phases=" << std::to_string(ph == PH1_NEWVIEW)
                         << ";safety="    << std::to_string((prefixLockedInHashes || v2 > this->prefixLockedView))
                         << KNRM << std::endl;
  }
  if (DEBUG) std::cout << "TEEverifyProposal failed" << std::endl;
  return Just(false, RDataPara(), Signs());
}

Just TrustedPara::TEEprepare(Stats &stats, Nodes nodes, PBlock block, Just just) {
  RDataPara  rd = just.getRDataPara();
  Hash   h2 = rd.getJusth();
  View   v2 = rd.getJustv();
  Phase1 ph = rd.getPhase();

  bool teeverif_result = TEEverify(stats , nodes, just);
  bool eq_views_result = this->view == rd.getPropv();
  bool eq_phases_result = ph == PH1_NEWVIEW;
 
  if (DEBUG) {
    std::cout << "TEEverify result: " << teeverif_result << std::endl;
    std::cout << "eq_views result: " << eq_views_result << " (this->view: " << this->view << ", rd.getPropv(): " << rd.getPropv() << ")" << std::endl;
    std::cout << "eq_phases result: " << eq_phases_result << " (ph: " << ph << ", PH1_NEWVIEW: " << PH1_NEWVIEW << ")" << std::endl;
     }


  if (TEEverify(stats,nodes,just)
      && this->view == rd.getPropv()
      && ph == PH1_NEWVIEW)
      // && (h2 == this->prefixLockedHash || v2 > this->prefixLockedView)) 
      { // AE-TODO : Add check if we have voted for this sequnce number
    //return sign(hash,h2,v2);
    return signBlock(block.hash(),h2,v2, block.getSeqNumber());
  } else {
    if (DEBUG) std::cout << KMAG << "TEEprepare failed:"
                         << "TEEverif="   << std::to_string(TEEverify(stats,nodes,just))
                         << ";eq-views="  << std::to_string(this->view == rd.getPropv())
                         << ";eq-phases=" << std::to_string(ph == PH1_NEWVIEW)
                         << ";safety="     << std::to_string((h2 == this->prefixLockedHash || v2 > this->prefixLockedView))
                         << KNRM << std::endl;
  }
  if (DEBUG) std::cout << "TEEprepare failed" << std::endl;
  return Just(false, RDataPara(), Signs());
}

Just TrustedPara::TEEstore(Stats &stats, Nodes nodes, Just just, bool allBlocksReceived) {
  Hash   h  = just.getRDataPara().getProph();
  View   v  = just.getRDataPara().getPropv();
  Phase1 ph = just.getRDataPara().getPhase();
  unsigned int seq = just.getRDataPara().getSeqNumber();
  // if (DEBUG) std::cout << "after getting stuff " << std::endl;

  if (DEBUG) std::cout << "RDATA: " << just.getRDataPara().prettyPrint() << std::endl;

  bool qsize_result = just.getSigns().getSize() == this->qsize;
  bool teeverif_result = TEEverify(stats, nodes, just);
  bool eq_views_result = this->view == v;
  bool eq_phases_result = ph == PH1_PREPARE || ph == PH1_PRECOMMIT;

  if (DEBUG) {
    std::cout << "qsize result: " << qsize_result << " (just.getSigns().getSize(): " << just.getSigns().getSize() << ", this->qsize: " << this->qsize << ")" << std::endl;
    std::cout << "TEEverify result: " << teeverif_result << std::endl;
    std::cout << "eq_views result: " << eq_views_result << " (this->view: " << this->view << ", v: " << v << ")" << std::endl;
    std::cout << "eq_phases result: " << eq_phases_result << " (ph: " << ph << ")" << std::endl;
    }

  if (qsize_result
      && teeverif_result
      && eq_views_result
      && eq_phases_result) {
    this->latestPreparedHash=h; this->latestPreparedView=v;
    if (ph == PH1_PRECOMMIT) { 
      // if we have all sequence numbers below this one, we lock it
      // AE-TODO: If we now have the prefix until some higher block, make sure to lock that one
      if (allBlocksReceived) {
        if (DEBUG) std::cout << "Locking block with seq number: " << seq << std::endl;
        this->prefixLockedHash=h; this->prefixLockedView=v; 
        }
      } //   AE-TODO: Implement this
    // return sign(h,Hash(),View());
    return signBlock(h,Hash(),View(),seq);
  }
  if (DEBUG) std::cout << "TEEstore failed" << std::endl;
  return Just(false, RDataPara(), Signs());
}
