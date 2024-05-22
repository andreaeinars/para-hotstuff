#include <stdio.h>
#include <stdlib.h>
#include <iostream>

#include "RDataPara.h"


Hash   RDataPara::getProph()  { return (this->proph); }
View   RDataPara::getPropv()  { return (this->propv); }
Hash   RDataPara::getJusth()  { return (this->justh); }
View   RDataPara::getJustv()  { return (this->justv); }
Phase1 RDataPara::getPhase()  { return (this->phase); }
unsigned int RDataPara::getSeqNumber() { return this->seqNumber; }


void RDataPara::serialize(salticidae::DataStream &data) const {
  data << this->proph << this->propv << this->justh << this->justv << this->phase << this->seqNumber;
}


void RDataPara::unserialize(salticidae::DataStream &data) {
  data >> this->proph >> this->propv >> this->justh >> this->justv >> this->phase >> this->seqNumber;
}


RDataPara::RDataPara(Hash proph, View propv, Hash justh, View justv, Phase1 phase, unsigned int seqNumber) {
  this->proph=proph;
  this->propv=propv;
  this->justh=justh;
  this->justv=justv;
  this->phase=phase;
  this->seqNumber=seqNumber;
}


RDataPara::RDataPara() {
  this->proph=Hash();
  this->propv=0;
  this->justh=Hash();
  this->justv=0;
  this->phase=PH1_NEWVIEW;
  this->seqNumber=0;
}


RDataPara::RDataPara(salticidae::DataStream &data) {
  unserialize(data);
}

void RDataPara::setPhase(Phase1 phase) {
  phase = phase;
}


std::string phase2stringPara(Phase1 phase) {
  if (phase == PH1_NEWVIEW) { return "PH_NEWVIEW"; }
  else if (phase == PH1_RECOVER) { return "PH_RECOVER"; }
  else if (phase == PH1_VERIFY) { return "PH_VERIFY"; }
  else if (phase == PH1_PREPARE) { return "PH_PREPARE"; }
  else if (phase == PH1_PRECOMMIT) { return "PH_PRECOMMIT"; }
  else if (phase == PH1_COMMIT) { return "PH_COMMIT"; }
  else { return ""; }
  return "";
}


std::string RDataPara::prettyPrint() {
  return ("RDATA-P[" + (this->proph).prettyPrint() + "," + std::to_string(this->propv)
          + "," + (this->justh).prettyPrint() + "," + std::to_string(this->justv)
          + "," + phase2stringPara(this->phase) + "," + std::to_string(this->seqNumber)
          + "]");
}

std::string RDataPara::toString() {
  return ((this->proph).toString() + std::to_string(this->propv)
          + (this->justh).toString() + std::to_string(this->justv)
          + std::to_string(this->phase) + std::to_string(this->seqNumber));
}


bool RDataPara::operator==(const RDataPara& s) const {
  if (DEBUG1) {
    std::cout << KYEL
              << "[1]" << (this->proph == s.proph)
              << "[2]" << (this->propv == s.propv)
              << "[3]" << (this->justh == s.justh)
              << "[4]" << (this->justv == s.justv)
              << "[5]" << (this->phase == s.phase)
              << "[6]" << (this->seqNumber == s.seqNumber)
              << KNRM << std::endl;
  }
  return (this->proph == s.proph
          && this->propv == s.propv
          && this->justh == s.justh
          && this->justv == s.justv
          && this->phase == s.phase
          && this->seqNumber == s.seqNumber);
}
