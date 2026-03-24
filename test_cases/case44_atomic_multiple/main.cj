// case44: 多个原子变量测试
// 测试多个原子变量同时使用（无竞争）

main() {
    var a = Atomic(1)
    var b = Atomic(2)
    var c = Atomic(3)
    
    spawn {
        a.fetchAdd(1)
        b.fetchAdd(1)
    }
    
    spawn {
        b.fetchAdd(1)
        c.fetchAdd(1)
    }
    
    spawn {
        a.fetchAdd(1)
        c.fetchAdd(1)
    }
}