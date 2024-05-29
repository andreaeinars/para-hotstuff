#include <stdio.h>
#include <stdlib.h>
#include <iostream>
#include <string>
#include <cstring>

#include "TrustedPara.h"


TrustedPara::TrustedPara() {
  this->latestPreparedHash = Hash(true); // the genesis block
  this->latestPreparedView = 0;
  this->latestPreparedSeqNumber = 0;
  this->prefixLockedHash = Hash(true); // the genesis block
  this->prefixLockedView = 0;
  this->prefixLockedSeqNumber = 0;
  this->view   = 0;
  this->phase  = PH1_NEWVIEW;
  this->qsize  = 0;
}

TrustedPara::TrustedPara(PID id, KEY priv, unsigned int q) {
  this->latestPreparedHash = Hash(true); // the genesis block
  this->latestPreparedView = 0;
  this->latestPreparedSeqNumber = 0;
  this->prefixLockedHash = Hash(true); // the genesis block
  this->prefixLockedView = 0;
  this->prefixLockedSeqNumber = 0;
  this->view   = 0;
  this->phase  = PH1_NEWVIEW;
  this->id     = id;
  this->priv   = priv;
  this->qsize  = q;
}

void TrustedPara::changeView(View v) {
  this->view = v;
  this->phase = PH1_NEWVIEW;
  blockPhases.clear();
  //prefixLockedSeqNumber = 0;
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
    increment_view();
  }
}

void TrustedPara::increment_block_phase(Hash blockHash) {
  if (blockPhases.find(blockHash) == blockPhases.end()) { //AE-TODO: Not sure this is needed
    blockPhases[blockHash] = PH1_PREPARE;
    this->phase = PH1_PARALLEL;
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

void TrustedPara::increment_view() {
  this->view++;
  blockPhases.clear();
  prefixLockedSeqNumber = 0;
}

void TrustedPara::set_phase(Phase1 phase) {
  this->phase = phase;
}

Just TrustedPara::sign(Hash h1, Hash h2, View v2, unsigned int seqNumber) {
  RDataPara rdata(h1,this->view,h2,v2,this->phase, seqNumber); //todo add sequnce number
  Sign sign(this->priv,this->id,rdata.toString());
  Just just(rdata,sign);
  increment_node_phase();
  return just;
}

Just TrustedPara::signBlock(Hash h1, Hash h2, View v2, unsigned int seqNumber) {
   if (blockPhases.find(h1) == blockPhases.end()) { //AE-TODO: Not sure this is needed
        blockPhases[h1] = PH1_PREPARE;
  }
  Phase1 ph = blockPhases[h1];
  RDataPara rdata(h1,this->view,h2,v2,ph, seqNumber); //todo add sequnce number
  Sign sign(this->priv,this->id,rdata.toString());
  Just just(rdata,sign);
  increment_block_phase(h1);
  return just;
}

Just TrustedPara::TEEsign(Stats &stats) {
  auto start = std::chrono::steady_clock::now();
  Just j = sign(Hash(false),this->latestPreparedHash,this->latestPreparedView, this->latestPreparedSeqNumber); // AE-TODO: Actuaclly implement this
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
  bool prefixLockedInHashes = (rd.getJustv() == 0) || (std::find(blockHashes.begin(), blockHashes.end(), prefixLockedHash) != blockHashes.end());
  bool teeverif_result = TEEverify(stats, nodes, just);
  bool eq_views_result = this->view == rd.getPropv();
  bool eq_phases_result = rd.getPhase() == PH1_NEWVIEW;
  bool safety_result = prefixLockedInHashes || rd.getJustv() > this->prefixLockedView;

  if (teeverif_result && eq_views_result && eq_phases_result && safety_result) {
    return just;
  }
  if (DEBUG) std::cout << KMAG << "TEEverifyProposal failed:" << "TEEverif=" << std::to_string(teeverif_result)<< ";eq-views=" << std::to_string(eq_views_result)
                         << ";eq-phases=" << std::to_string(eq_phases_result) << ";safety="    << std::to_string(safety_result) << KNRM << std::endl;
  return Just(false, RDataPara(), Signs());
}

Just TrustedPara::TEEprepare(Stats &stats, Nodes nodes, PBlock block, Just just) {
  RDataPara  rd = just.getRDataPara();
  bool teeverif_result = TEEverify(stats , nodes, just);
  bool eq_views_result = this->view == rd.getPropv();
  bool eq_phases_result = rd.getPhase() == PH1_NEWVIEW;
 
  if (teeverif_result && eq_views_result && eq_phases_result) { 
    // storedBlocks[block.getSeqNumber()] = block;
    return signBlock(block.hash(),rd.getJusth(),rd.getJustv(), block.getSeqNumber());
  }
  if (DEBUG) std::cout << KMAG << "TEEprepare failed:" << "TEEverif=" << std::to_string(teeverif_result) << ";eq-views="  << std::to_string(eq_views_result)
                         << ";eq-phases=" << std::to_string(eq_phases_result) << KNRM << std::endl;
  return Just(false, RDataPara(), Signs());
}

Just TrustedPara::TEEstore(Stats &stats, Nodes nodes, Just just, std::function<PBlock(unsigned int)> getBlockFunc) {
  Hash   h  = just.getRDataPara().getProph();
  View   v  = just.getRDataPara().getPropv();
  Phase1 ph = just.getRDataPara().getPhase();
  Hash justH = just.getRDataPara().getJusth();
  View justV = just.getRDataPara().getJustv();
  unsigned int seq = just.getRDataPara().getSeqNumber();

  bool qsize_result = just.getSigns().getSize() == this->qsize;
  bool teeverif_result = TEEverify(stats, nodes, just);
  bool eq_views_result = this->view == v;
  bool eq_phases_result = ph == PH1_PREPARE || ph == PH1_PRECOMMIT;

  if (qsize_result && teeverif_result && eq_views_result && eq_phases_result) {
    if (v > this->latestPreparedView || (v == this->latestPreparedView && seq > this->latestPreparedSeqNumber)) { // Update latest prepared block
      this->latestPreparedHash = h; this->latestPreparedView = v; this->latestPreparedSeqNumber = seq;
    }

    if (ph == PH1_PRECOMMIT) { 
      precommitData[seq] = {h, v};
      unsigned int highestContinuousSeq = 0;
      Hash lastValidHash = this->prefixLockedHash;
      unsigned int checkFrom = (prefixLockedView == this->view) ? this->prefixLockedSeqNumber + 1 : 1;

      bool prevBlockExists = true;
      for (unsigned int i = checkFrom; i <= precommitData.rbegin()->first; ++i) { // Go till the highest seqNumber in precommitData
        if (precommitData.find(i) == precommitData.end()) {
            if (DEBUG) std::cout << "Missing precommit for seq number: " << i << std::endl;
            break;  // Missing a sequence number
        }

        bool blockExists = getBlockFunc(i).isBlock();
        if (blockExists) {
            if (prevBlockExists && (i > 1) && !getBlockFunc(i).extends(lastValidHash)) {
                if (DEBUG) std::cout << "Block with seq number: " << i << " does not extend correctly" << std::endl;
                break;  // Block does not correctly extend the previous block
            }
            lastValidHash = getBlockFunc(i).hash();
        }
        
        prevBlockExists = blockExists;
        highestContinuousSeq = i;
      }
      if (highestContinuousSeq > this->prefixLockedSeqNumber) {
        if (DEBUG) std::cout << "Locking block with seq number: " << highestContinuousSeq << std::endl;
        this->prefixLockedHash = precommitData[highestContinuousSeq].blockHash;
        this->prefixLockedView = precommitData[highestContinuousSeq].view;
        this->prefixLockedSeqNumber = highestContinuousSeq;
      }
    }
    return signBlock(h,justH,justV,seq);
  }
  
  if (DEBUG) std::cout << "TEEstore failed" << std::endl;
  return Just(false, RDataPara(), Signs());
}


