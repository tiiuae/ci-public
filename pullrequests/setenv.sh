
PRDIR="$(pwd)"

# Correct relative path for hydra.default to function correctly
cd ../containers && . confs/hydra.default
cd "${PRDIR}"

export HYDRACTL_USERNAME="automation"
#HYDRACTL_PASSWORD for HYDRACTL_USERNAME needs to be setup also, do not use this file in order not to accidentally saving to public repo
# TODO: Get the password automatically from hydra configuration.
export TOKENFILE="./tokenfile"
export TESTREPO="tiiuae/ghaf"
export ORGANIZATION="tiiuae"
export BUILDPRSFILE="pr2_data"
export BUILDCHANGEDPRSFILE="pr2_changed_data"
export HYDRACTL="../hydractl/hydractl.py" 
export EXT_PORT="${HC_PORT}"
export RUNDELAY="15"
