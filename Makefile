######## My Settings ########

SALTICIDAE=$(realpath ./salticidae)
Salticidae_Include_Paths = -I$(SALTICIDAE)/include
Salticidae_Lib_Paths = -L$(SALTICIDAE)/lib

CFLAGS = `pkg-config --cflags libcrypto openssl libuv` # gio-2.0 openssl
LDLIBS = `pkg-config --libs   libcrypto openssl libuv` #-lgmp # gio-2.0 openssl

######## App Settings ########

App_Cpp_Files := $(wildcard App/*.cpp) \
				 $(wildcard App/utils/*.cpp) \
				 $(wildcard App/handlers/*.cpp) 
App_Cpp_Files := $(filter-out App/Client.cpp App/Server.cpp, $(App_Cpp_Files))
App_Include_Paths := -IApp $(Salticidae_Include_Paths)

App_Cpp_Flags := -fPIC -Wno-attributes $(App_Include_Paths) -std=c++17 $(CFLAGS)
App_Link_Flags := $(LDLIBS) $(Salticidae_Lib_Paths) -lsalticidae
App_Cpp_Objects := $(App_Cpp_Files:.cpp=.o)

App_Name := app

.PHONY: all run

all: $(App_Name)

run: all
	@$(CURDIR)/$(App_Name)
	@echo "RUN  =>  $(App_Name) [OK]"

######## App Objects ########

server: App/Server.o $(App_Cpp_Objects) 
	@$(CXX) $^ -o $@ $(App_Link_Flags) $(Salticidae_Include_Paths)
	@echo "LINK => $@"

client: App/Client.o App/utils/Stats.o App/utils/Signs.o App/utils/Sign.o App/utils/Nodes.o App/utils/NodeInfo.o App/utils/KeysFun.o App/utils/Transaction.o
	@$(CXX) $^ -o $@ $(App_Link_Flags) $(Salticidae_Include_Paths)
	@echo "LINK => $@"

keys: App/utils/Keys.o App/utils/KeysFun.o 
	@$(CXX) $^ -o $@ $(App_Link_Flags) $(Salticidae_Include_Paths)
	@echo "LINK => $@"

App/%.o: App/%.cpp
	@$(CXX) $(App_Cpp_Flags) -c $< -o $@
	@echo "CXX  <=  $<"

$(App_Name): $(App_Cpp_Objects)
	@$(CXX) $^ -o $@ $(App_Link_Flags)
	@echo "LINK =>  $@"

.PHONY: clean

clean:
	@rm -f $(App_Name) $(App_Cpp_Objects)
