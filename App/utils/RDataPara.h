#ifndef RDATAPARA_H
#define RDATAPARA_H

#include "config.h"
#include "types.h"
#include "Hash.h"

#include "salticidae/stream.h"

// Round Data
class RDataPara {
 private:
  Hash   proph;
  View   propv = 0;
  Hash   justh;
  View   justv = 0;
  Phase1 phase;
  unsigned int seqNumber = 0;

 public:
  RDataPara(Hash proph, View propv, Hash justh, View justv, Phase1 phase, unsigned int seqNumber);
  RDataPara(salticidae::DataStream &data);
  RDataPara();

  Hash   getProph();
  View   getPropv();
  Hash   getJusth();
  View   getJustv();
  Phase1 getPhase();
  unsigned int getSeqNumber();

  void setPhase(Phase1 phase);

  void serialize(salticidae::DataStream &data) const;
  void unserialize(salticidae::DataStream &data);

  std::string prettyPrint();
  std::string toString();

  bool operator==(const RDataPara& s) const;
};


#endif
